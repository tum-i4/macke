"""
One main function, that just calls all analysis
"""
from .helper import arg_parse_mackedir
from .functions import main as functions
from .kleecrash import main as kleecrash
from .linecoverage import main as linecoverage
from .runtime import main as runtime
from .vulninst import main as vulninst


def main():
    # Parse the arguments and give corresponding -h information
    arg_parse_mackedir("Adds lots of analyzes to a MACKE directory")

    # Just call all mains from all analyzes scripts
    functions()
    kleecrash()
    linecoverage()
    runtime()
    vulninst()

if __name__ == '__main__':
    main()
