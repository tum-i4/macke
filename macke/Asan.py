
from os import path

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
            self.file, self.line = self.get_vulnerable_instruction()


    def get_vulnerable_instruction(self):
        assert self.iserror
        if self.stack:
            location = self.stack[0][1]
            # Split into file, linenumber
            splits = location[:location.rfind(':')].split(':')
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
                self.description = description.split(b' ')[0].decode("utf-8")

        self.stack = []
        if self.has_stack_trace():
            # line number and frame-number
            lno = 0
            fno = 0

            while b"#0" not in lines[lno]:
                lno += 1

            while lno < len(lines) and b"#%d" % fno in lines[lno]:
                words = lines[lno].strip().split(b' ')

                # function name is 4th word
                fname = words[3].decode("utf-8")

                # location is 5th word
                location = words[4].decode("utf-8")
                self.stack.append((fname, location))
                lno += 1
                fno += 1

    def convert_to_ktest(self, fuzzmanager, directory, testname, kleeargs = []):
        """
        Creates a file <testname>.ktest and <testname>.ktest.err in directory
        Returns the name of the errfile
        """
        ktestname = path.join(directory, testname + ".ktest")
        ktesterrorname = path.join(directory, testname + ".fuzz.err")

        # Generate .ktest file
        fuzzmanager.run_ktest_converter(self.analyzedfunc, self.inputfile, ktestname, kleeargs)

        # Generate .ktest.err file
        errcontent = ("Error: " + self.description + "\n"
                   + "File: " + self.file + "\n"
                   + "Line: " + self.line + "\n"
                   # Dummy assembly.ll line
                   + "assembly.ll line: 0\n"
                   + "Stack:\n")
        # Now only add stack to errcontent
        for i in range(0, len(self.stack)):
            # The first number is the stack frame number + line number in assembly (here dummy 0)
            errcontent += "\t#" + str(i) + "0000000"
            # Function name + <unknown> arguments - to be tested
            errcontent += " in " + self.stack[i][0] + "(<unknown>)"
            # at location
            errcontent += " at " + self.stack[i][1] + "\n"

        f = open(ktesterrorname, "w")
        f.write(errcontent)
        f.close()

        return ktesterrorname




