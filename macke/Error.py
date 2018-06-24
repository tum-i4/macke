"""
Storage wrapper for Errors found by KLEE
"""
from collections import OrderedDict
from functools import total_ordering
from os import path

from .StackTrace import StackTrace

@total_ordering
class Error:
    program_functions = []

    def set_program_functions(program_functions):
        Error.program_functions = program_functions

    def get_function_name(function):
        if function not in Error.program_functions and '.' in function:
            # remove everything after the dot
            tmp = function[:function.index('.')]
            if tmp in Error.program_functions:
                return tmp
        return function

    """
    Container class for all information about errors found by KLEE
    """
    def __init__(self, errfile, entryfunction):
        entryfunction = Error.get_function_name(entryfunction)
        # Store the function, that was used as an entry point on the test case
        self.entryfunction = entryfunction

        # Store the path and name of the .err-file generate by KLEE
        self.errfile = errfile

        # Store the path and name of the corresponding .ktest-file
        self.ktestfile = get_corresponding_ktest(errfile)

        # Store the reason for the error
        self.reason = get_reason_for_error(errfile)

        # Store an identifier for the vulnerable instruction "file:line"
        self.vulnerable_instruction = get_vulnerable_instruction(errfile)

        # Store the stack trace for comparison
        self.stacktrace = get_stacktrace(errfile, entryfunction)

    def __eq__(self, other):
        return ((self.entryfunction, self.errfile, self.reason,
                 self.vulnerable_instruction) ==
                (other.entryfunction, other.errfile, other.reason,
                 other.vulnerable_instruction))

    def __lt__(self, other):
        return ((self.vulnerable_instruction, self.entryfunction,
                 self.errfile) < (other.vulnerable_instruction,
                                  other.entryfunction, other.errfile))

    def __str__(self):
        return "<%s, %s, %s, %s>" % (
            self.entryfunction, self.errfile, self.reason,
            self.vulnerable_instruction)

    def __repr__(self):
        return "<macke.Error.Error object: %s, %s, %s, %s>" % (
            self.entryfunction, self.errfile, self.reason,
            self.vulnerable_instruction)

    def is_blacklisted(self):
        """
        Exclude some error reasons, that are not helpful for further analysis
        """
        # klee_get_obj_size can be removed, if KLEE fixes bug #458
        # See: https://github.com/klee/klee/issues/458
        return "klee_get_obj_size" in self.reason

    def as_ordered_dict(self):
        """ Get all informations about this error in an ordered dict """
        return OrderedDict([
            ("entryfunction", self.entryfunction),
            ("errfile", self.errfile),
            ("ktestfile", self.ktestfile),
            ("reason", self.reason),
            ("vulnerableInstruction", self.vulnerable_instruction),
        ])


def get_corresponding_kleedir(errfile):
    """ Get the path of the corresponding klee directory """
    return path.dirname(errfile)


def get_corresponding_kleedir_name(errfile):
    """ Get the name of the corresponding klee directory """
    return path.basename(path.dirname(errfile))


def get_corresponding_ktest(errfile):
    """ Get the corresponding ktest file for a .err file """
    assert errfile.endswith(".err")
    assert errfile.count(".") >= 2

    # some/path/test123456.type.err
    return errfile[:errfile[:-4].rfind(".")] + ".ktest"


def get_reason_for_error(errfile):
    """ Extract the reason for an error from a .err file """
    assert path.isfile(errfile)

    with open(errfile, "r", errors='ignore') as file:
        reason = file.readline()
        # The reason starts with "Error: "
        return reason[len("Error: "):].strip()
    return ""


def get_vulnerable_instruction(errfile):
    """ Extract the vulnerable instruction "file:line" from a .err file """
    assert path.isfile(errfile)

    with open(errfile, "r", errors='ignore') as file:
        # The first line contains the reason - irrelevant for vuln inst
        file.readline()

        # Check whether klee info is existent and use it in case there is no stack trace
        nextline = file.readline().strip()
        if nextline.startswith("File: "):
            klee_flinfo_exists = True
            filenameline = nextline[len("File: "):]
            linenumline = int(file.readline().strip()[len("line: "):])
        else:
            klee_flinfo_exists = False

        for line in file:
            if line.startswith('Stack:'):
                break

        for line in file:
            if line.startswith('Info:'):
                break
            words = line.strip().split(' ')

            # function name is 3th word
            fname = words[2]

            # Don't use external functions as vulnerable instruction
            if fname not in Error.program_functions:
                continue

            # Don't put __macke_error as vulnerable instruction
            if fname.startswith("__macke_error_"):
                continue

            # location is the last word
            location = words[-1]

            # The location is already in the format filename:line, thus use it directly
            return location

        if klee_flinfo_exists:
            return "%s:%s" % (filenameline, linenumline)
    return ""


def get_stacktrace(errfile, entryfunction):
    """ Extract the relevant parts of the stack trace from a .err file """
    assert path.isfile(errfile)

    with open(errfile, 'r', errors='ignore') as err:
        for line in err:
            if line.startswith('Stack:'):
                break

        stack = []
        for line in err:
            if line.startswith('Info:'):
                break
            words = line.strip().split(' ')

            # function name is 3th word
            fname = Error.get_function_name(words[2])

            # Don't put external functions in stack trace
            if fname not in Error.program_functions:
                continue

            # Don't put __macke_error helper functions in stack trace
            if fname.startswith("__macke_error_"):
                continue

            # location is last word
            location = words[-1]
            stack.append((fname, location))
    return StackTrace(stack, entryfunction)
