"""
Registry for Errors found by KLEE
"""
from os import path, listdir
from .constants import ERRORFILEEXTENSIONS
from .Error import Error


class ErrorRegistry:
    """
    A registry for errors found by KLEE, that allows quick access and filters
    """

    def __init__(self):
        # Initialize some hash tables for quick access
        # Note: Python stores pointers to objects, not copies of the objects
        self.forfunction = dict()
        self.forvulninst = dict()
        self.forerrfile = dict()
        self.mackeforerrfile = dict()

        self.errorcounter = 0
        self.mackerrorcounter = 0

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
        self.forerrfile[error.errfile] = error
        self.errorcounter += 1

        if error.errfile.endswith(".macke.err"):
            self.mackerrorcounter += 1

            # Find the previous error
            # "ERROR FROM /path/test0000001.ptr.err"
            testfrom = error.reason[len("ERROR FROM "):].strip()
            preverr = self.forerrfile[testfrom]
            add_to_listdict(self.mackeforerrfile, testfrom, error)

            # Propagate information about the vulnerable instruction
            error.vulnerableInstruction = str(preverr.vulnerableInstruction)

        add_to_listdict(self.forvulninst, error.vulnerableInstruction, error)

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
