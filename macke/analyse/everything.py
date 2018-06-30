"""
One main function, that just calls all analysis
"""
from .chains import main as chains
from .functions import main as functions
from .helper import arg_parse_mackedir
from .kleecrash import main as kleecrash
from .aflabort import main as aflabort
from .linecoverage import main as linecoverage
from .partial import main as partial
from .runtime import main as runtime
from .vulninsts import main as vulninsts


def main():
    """
    One function, that calls all analysis functions and thereby generates
    multiple jsons inside a MACKE directory
    """
    # Parse the arguments and give corresponding -h information
    arg_parse_mackedir("Adds lots of analyzes to a MACKE directory")

    # Just call all mains from all analyzes scripts
    chains()
    functions()
    kleecrash()
    aflabort()
    linecoverage()
    partial()
    runtime()
    vulninsts()

if __name__ == '__main__':
    main()
