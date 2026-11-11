#pragma once

#include <inttypes.h>
#include <algorithm>

namespace Arcanum
{
    class TimeManager
    {
        public:
        static int64_t getMoveTimeAllocation(int64_t moveTime, int64_t moveOverhead)
        {
            return std::max<int64_t>(moveTime - moveOverhead, 1);
        }

        static int64_t getTimeAllocationMovesToGo(int64_t time, int64_t inc, int64_t movesToGo, int64_t moveOverhead)
        {
            return std::min(std::max<int64_t>((time / (movesToGo + 2)) + 3*inc/4 - moveOverhead, 1), time - moveOverhead);
        }

        static int64_t getTimeAllocation(int64_t time, int64_t inc, int64_t moveOverhead)
        {
            int64_t allocation = std::min((time / 30) + 3*inc/4, time / 2);
            return std::max<int64_t>(allocation - moveOverhead, 1);
        }

        static int64_t getMaxTimeAllocation(int64_t time, int64_t inc, int64_t moveOverhead)
        {
            int64_t softAllocation = getTimeAllocation(time, inc, moveOverhead);
            return std::min(4 * softAllocation, (time / 2) - moveOverhead);
        }

        static int64_t getMaxTimeAllocationMovesToGo(int64_t time, int64_t inc, int64_t movesToGo, int64_t moveOverhead)
        {
            int64_t softAllocation = getTimeAllocationMovesToGo(time, inc, movesToGo, moveOverhead);
            int64_t limit = std::min((8 * time / 10), (3 * time / (movesToGo + 2)));
            return std::min(4 * softAllocation, limit - moveOverhead);
        }

    };
}