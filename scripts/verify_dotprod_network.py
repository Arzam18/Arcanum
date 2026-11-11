#!/usr/bin/env python3
"""Check that Arcanum's quantized L1 weights can use the exact SDOT packing."""

from __future__ import annotations

import math
import random
import struct
import sys
from pathlib import Path

MAGIC = b"Arcanum FNNUE v7"
L1_SIZE = 1024
BUCKETS = 8
LQ = 64


def round_away(value: float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def take_u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated NNUE header")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <network.fnnue>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    data = path.read_bytes()
    offset = 0
    magic_size, offset = take_u32(data, offset)
    if data[offset:offset + magic_size] != MAGIC:
        raise ValueError("unexpected Arcanum NNUE magic")
    offset += magic_size
    metadata_size, offset = take_u32(data, offset)
    offset += metadata_size

    # Skip the 768 x 1024 feature-transformer floats and its 1024 biases.
    offset += (768 * L1_SIZE + L1_SIZE) * 4
    if offset > len(data):
        raise ValueError("truncated feature transformer")

    rng = random.Random(0xA7CA)
    maximum_abs_weight = 0
    global_high_min, global_high_max = 128, -129
    buckets_using_single_sdot = 0
    buckets_dotprod_eligible = 0
    buckets_neon_fallback = 0

    for bucket in range(BUCKETS):
        raw_weights = struct.unpack_from("<1024f", data, offset)
        offset += L1_SIZE * 4
        offset += 4  # output bias
        weights = [round_away(value * LQ) for value in raw_weights]
        # Match the engine's int16_t quantization conversion.
        weights = [((value + 32768) & 0xFFFF) - 32768 for value in weights]

        lows: list[int] = []
        highs: list[int] = []
        eligible = True
        for weight in weights:
            low = weight & 0xFF
            if low >= 128:
                low -= 256
            high = (weight - low) // 256
            if not -128 <= high <= 127:
                eligible = False
                break
            lows.append(low)
            highs.append(high)
            maximum_abs_weight = max(maximum_abs_weight, abs(weight))
            global_high_min = min(global_high_min, high)
            global_high_max = max(global_high_max, high)

        if not eligible:
            buckets_neon_fallback += 1
            continue

        buckets_dotprod_eligible += 1
        high_zero = all(high == 0 for high in highs)
        buckets_using_single_sdot += int(high_zero)

        # Test the precise centering/correction used by the C++ kernel.
        activations = [rng.randrange(256) for _ in range(L1_SIZE)]
        scalar = sum(a * w for a, w in zip(activations, weights))
        dot_low = sum((a - 128) * low for a, low in zip(activations, lows))
        dot_high = sum((a - 128) * high for a, high in zip(activations, highs))
        correction = 128 * sum(weights)
        packed = dot_low + 256 * dot_high + correction
        if scalar != packed:
            raise AssertionError(f"bucket {bucket}: SDOT decomposition changed the NNUE sum")

    if offset != len(data):
        raise ValueError(f"unexpected trailing network data: {len(data) - offset} bytes")

    if buckets_dotprod_eligible == 0:
        raise ValueError("no output bucket can be represented by the exact SDOT byte decomposition")

    print(f"PASS: {path.name}; {buckets_dotprod_eligible}/{BUCKETS} buckets preserve exact int16 arithmetic through SDOT.")
    print(f"Quantized L1 weight range is bounded by +/-{maximum_abs_weight}.")
    print(f"Signed high-byte range: {global_high_min}..{global_high_max}.")
    print(f"Buckets that need only one SDOT stream: {buckets_using_single_sdot}/{buckets_dotprod_eligible}.")
    print(f"Buckets safely falling back to NEON 16-bit multiply: {buckets_neon_fallback}/{BUCKETS}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
