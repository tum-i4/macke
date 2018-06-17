
from os import path
import re

class AsanResult:
    """
    Container, that stores all information about a program run with asan
    """

    def __init__(self, program_output, inputfile, analyzedfunc):
        self.analyzedfunc = analyzedfunc
        self.inputfile = inputfile
        self.output = program_output
        self.iserror = b"==ERROR:" in self.output

        if self.iserror:
            self.parse_asan_output()

        # parse_asan_output might decide to set iserror to False
        if self.iserror:
            self.file, self.line = self.get_vulnerable_instruction()


    def get_vulnerable_instruction(self):
        assert self.iserror
        if self.stack:
            location = self.stack[0][1]
            # Split into file, linenumber
            splits = location.split(':')
            if len(splits) > 1:
                return splits[0], splits[1]
            return splits[0], "0"
        return "<Unknown>", "0"

    def has_stack_trace(self):
        """ Return true if stack trace data is found """
        # Check for "#0" and "#1"
        return b"#0" in self.output and b"#1" in self.output

    def parse_asan_output(self):
        assert self.iserror

        lines = self.output.splitlines()
        for line in lines:
            # Get the first word after the "Sanitizer:" string on the line that contains "==ERROR:"
            if b"==ERROR:" in line:
                description = line[line.find(b"Sanitizer:")+11:]
                description.strip()
                desc_parts = description.split(b' ')
                if b'on' in description:
                    self.description = b' '.join(desc_parts[0:desc_parts.index(b'on')]).decode("utf-8")
                else:
                    self.description = desc_parts[0].decode("utf-8", 'ignore').rstrip(':')

        self.stack = []
        has_location = re.compile("^.*:[0-9]+:[0-9]+$")
        if self.has_stack_trace():
            # line number and frame-number
            lno = 0
            fno = 0

            while b"#0" not in lines[lno]:
                lno += 1

            while lno < len(lines) and b"#%d" % fno in lines[lno]:
                words = lines[lno].strip().split(b' ')

                # function name is 4th word
                fname = words[3].decode("utf-8", 'ignore')

                # location is last word
                # careful because c++ names containing spaces (Relevant for asan functions)
                location = words[-1].decode("utf-8", 'ignore')
                # remove line offset for klee compatibility
                if has_location.match(location):
                    location = location[:location.rfind(":")]

                self.stack.append((fname, location))
                lno += 1
                fno += 1

        # Ignore errors where the argument was freed and gets freed (again) in our driver
        if (self.description.startswith("attempting double-free") and ((len(self.stack) > 2 and
            self.stack[1][0].startswith("__interceptor_") and self.stack[2][0].startswith("macke_fuzzer_driver")) or
            (len(self.stack) > 1 and self.stack[0][0].startswith("__interceptor_") and self.stack[1][0].startswith("macke_fuzzer_driver")))):
            self.iserror = False

    def convert_to_ktest(self, fuzzmanager, directory, testname, kleeargs = None):
        """
        Creates a file <testname>.ktest and <testname>.ktest.err in directory
        Returns the name of the errfile
        """
        ktestname = path.join(directory, testname + ".ktest")
        ktesterrorname = path.join(directory, testname + ".fuzz.err")

        if kleeargs is None:
            kleeargs = []

        # Generate .ktest file
        fuzzmanager.run_ktest_converter(self.analyzedfunc, self.inputfile, ktestname, kleeargs)

        # Generate .ktest.err file
        errcontent = ("Error: " + self.description + "\n"
                   + "File: " + self.file + "\n"
                   + "line: " + self.line + "\n"
                   # Dummy assembly.ll line
                   + "assembly.ll line: 0\n"
                   + "Stack:\n")
        # Now only add stack to errcontent
        for i in range(0, len(self.stack)):
            # The first number is the stack frame number + line number in assembly (here dummy 0)
            errcontent += "\t#" + str(i) + "0000000"
            # Function name + <unknown> arguments - to be tested
            errcontent += " in " + self.stack[i][0] + " (<unknown>)"
            # at location
            errcontent += " at " + self.stack[i][1] + "\n"

        f = open(ktesterrorname, "w")
        f.write(errcontent)
        f.close()

        return ktesterrorname




