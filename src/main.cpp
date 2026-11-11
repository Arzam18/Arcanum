#include <uci/uci.hpp>
#if !defined(ANDROID_UCI_ONLY)
#include <argsparser.hpp>
#endif
#include <eval.hpp>
#include <bitboardlookups.hpp>
#include <zobrist.hpp>

using namespace Arcanum;

int main(int argc, char *argv[])
{
    BitboardLookups::generateBitboardLookups();
    Zobrist::init();
    Evaluator::nnue.load(Interface::UCI::optionNNUEPath.value);

#if defined(ANDROID_UCI_ONLY)
    (void)argc;
    (void)argv;
    Interface::UCI::loop();
    return EXIT_SUCCESS;
#else
    if(argc == 1)
    {
        Interface::UCI::loop();
        return EXIT_SUCCESS;
    }

    if(!ArgsParser::parseArgumentsAndRunCommand(argc, argv))
    {
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
#endif
}