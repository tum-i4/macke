"""
Registry for Errors found by KLEE
"""
from os import listdir, path

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
        assert path.isdir(kleedir)

        for file in listdir(kleedir):
            if any(file.endswith(ext) for ext in ERRORFILEEXTENSIONS):
                self.create_entry(path.join(kleedir, file), entryfunction)

    def create_entry(self, errfile, entryfunction):
        """ Create a new error and add it to the registry """
        err = Error(errfile, entryfunction)

        if not err.is_blacklisted():
            self.register_error(err)

    def register_error(self, error):
        """ register an existing error """

        if error.errfile.endswith(".macke.err"):
            # Find the prepended error
            # "ERROR FROM /path/test0000001.ptr.err"
            testfrom = error.reason[len("ERROR FROM "):].strip()

            # Exclude all MACKE errors based on black listed errors
            if testfrom not in self.forerrfile:
                return

            self.mackerrorcounter += 1
            add_to_listdict(self.mackeforerrfile, testfrom, error)

            # Propagate information about the vulnerable instruction
            preverr = self.forerrfile[testfrom]
            error.vulnerable_instruction = str(preverr.vulnerable_instruction)
            error.stacktrace.prepend(preverr.stacktrace)

        add_to_listdict(self.forfunction, error.entryfunction, error)
        self.forerrfile[error.errfile] = error
        self.errorcounter += 1

        add_to_listdict(self.forvulninst, error.vulnerable_instruction, error)

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

    def get_all_vulninst_for_func(self, function):
        """
        Returns a set of all vulnerable instructions for a given function
        """
        if function not in self.forfunction:
            return set()

        result = set()
        for error in self.forfunction[function]:
            result.add(error.vulnerable_instruction)

        return result

    def to_prepend_in_phase_two(self, caller, callee, exclude_known=True):
        """
        Returns a set of .err-files, that should be prepended to callee for the
        analysis from caller. All these ktests belongs to a vulnerable
        instruction, that was not covered by an error from caller
        """
        if callee not in self.forfunction:
            return set()

        err_caller = self.forfunction[caller]
        err_callee = self.forfunction[callee]

        result = set()
        for err in err_callee:
            # Look whether it is already known
            if exclude_known and any(err.stacktrace.is_contained_in(err2.stacktrace) for err2 in err_caller):
                continue
            result.add(err.errfile)

        return result


def add_to_listdict(dictionary, key, value):
    """ Add an entry to a dictionary of lists """

    # Create slot for key, if this is the first entry for the key
    if key not in dictionary:
        dictionary[key] = []
    dictionary[key].append(value)
