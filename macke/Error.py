"""
Storage wrapper for Errors found by KLEE
"""
from os import path


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

        # Store the reason for the error
        self.reason = get_reason_for_error(errfile)

        # Store an identifier for the vulnerable instruction "file:line"
        self.vulnerableInstruction = get_vulnerable_instruction(errfile)

    def __str__(self):
        return "<%s, %s, %s, %s>" % (
            self.entryfunction, self.errfile, self.reason,
            self.vulnerableInstruction)

    def __repr__(self):
        return "<macke.Error.Error object: %s, %s, %s, %s>" % (
            self.entryfunction, self.errfile, self.reason,
            self.vulnerableInstruction)


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
