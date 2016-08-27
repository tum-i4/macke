"""
Storage for Error find by KLEE
"""
from os import path, listdir
from .constants import ERRORFILEEXTENSIONS


class ErrorRegistry:
    """
    A registry for errors found by KLEE, that allows quick access and filters
    """

    def __init__(self):
        # Initialize some hash tables for quick access
        # Note: Python stores pointers to objects, not copies of the objects
        self.forfunction = dict()
        self.forvulninst = dict()

        self.errorcounter = 0

    def create_from_dir(self, kleedir, entryfunction):
        """ register all errors from directory """
        assert(path.isdir(kleedir))

        for file in listdir(kleedir):
            if any(file.endswith(ext) for ext in ERRORFILEEXTENSIONS):
                self.create_entry(path.join(kleedir, file), entryfunction)

    def create_entry(self, errfile, entryfunction):
        """ Create a new error and add it to the registry """
        self.register_error(Error(errfile, entryfunction))

    def register_error(self, error):
        """ register an existing error """
        add_to_listdict(self.forfunction, error.entryfunction, error)
        add_to_listdict(self.forvulninst, error.vulnerableInstruction, error)
        self.errorcounter += 1

    def count_error_test_cases(self):
        """
        Count the number of ktests triggering any kind of error
        """
        return self.errorcounterr

    def count_vulnerable_instructions(self):
        """
        Count the number of vulnerable instructions stored in the registry
        """
        return len(self.forvulninst)

    def count_functions_with_errors(self):
        """
        Count the number of functions with at least one error in the registry
        """
        return len(self.forfunction)

    def get_all_vulnerable_instructions_for_function(self, function):
        """
        Returns a set of all vulnerable instructions for a given function
        """
        if function not in self.forfunction:
            return set()

        result = set()
        for error in self.forfunction[function]:
            result.add(error.vulnerableInstruction)

        return result

    def get_errfiles_to_prepend_in_phase_two(
            self, caller, callee, exclude_known=True):
        """
        Returns a set of .err-files, that should be prepended to callee for the
        analysis from caller. All these ktests belongs to a vulnerable
        instruction, that was not covered by an error from caller
        """
        if callee not in self.forfunction:
            return set()

        vi_caller = self.get_all_vulnerable_instructions_for_function(caller)
        vi_callee = self.get_all_vulnerable_instructions_for_function(callee)

        vitoprepend = vi_callee
        if exclude_known:
            vitoprepend -= vi_caller

        if not vitoprepend:
            return set()

        result = set()
        for err in self.forfunction[callee]:
            if err.vulnerableInstruction in vitoprepend:
                result.add(err.errfile)

        return result


def add_to_listdict(dictionary, key, value):
    """ Add an entry to a dictionary of lists """

    # Create slot for key, if this is the first entry for the key
    if key not in dictionary:
        dictionary[key] = []
    dictionary[key].append(value)


class Error:
    """
    Container class for all information about errors found by KLEE
    """

    def __init__(self, errfile, entryfunction):
        # Store the function, that was used as an entry point on the test case
        self.entryfunction = entryfunction

        # Store the path and name of the .err-file generate by KLEE
        self.errfile = errfile

        # Store the path and name of the corresponding .ktest-file
        self.ktestfile = get_corresponding_ktest(errfile)

        # Store an identifier for the vulnerable instruction "file:line"
        self.vulnerableInstruction = get_vulnerable_instruction(errfile)


def get_corresponding_ktest(errfile):
    """ Get the corresponding ktest file for a .err file """
    assert errfile.endswith(".err")
    assert errfile.count(".") >= 2

    # some/path/test123456.type.err
    return errfile[:errfile[:-4].rfind(".")] + ".ktest"


def get_reason_for_error(errfile):
    """ Extract the reason for an error from a .err file """
    assert path.isfile(errfile)

    with open(errfile, "r") as file:
        reason = file.readline()
        # The reason starts with "Error: "
        return reason[len("Error: "):].strip()
    return ""


def get_vulnerable_instruction(errfile):
    """ Extract the vulnerable instruction "file:line" from a .err file """
    assert path.isfile(errfile)

    with open(errfile, "r") as file:
        # The first line contains the reason - irrelevant for vuln inst
        file.readline()

        nextline = file.readline().strip()
        if nextline.startswith("File: "):
            filenameline = nextline[len("File: "):]
            linenumline = int(file.readline().strip()[len("line: "):])
            return "%s:%s" % (filenameline, linenumline)
    return ""
