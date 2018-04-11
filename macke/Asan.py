

class AsanResult:
    """
    Container, that stores all information about a program run with asan
    """

    def __init__(self, program_output):
        self.output = program_output
        self.iserror = "==ERROR:" in self.output

        if self.iserror:
            parse_asan_output(self.output)
            self.vulnerable_instruction = get_vulnerable_instruction()


    def get_vulnerable_instruction()
        assert self.iserror
        if stack:
            location = stack[0][1]
            return location[:location.rfind(':')]

    def has_stack_trace():
        """ Return true if stack trace data is found """
        # Check for "#0" and "#1"
        return "#0" in self.output and "#1" in self.output

    def parse_asan_output():
        assert self.iserror

        lines = self.output.splitlines()
        for line in lines:
            # Get the first word after the "Sanitizer:" string on the line that contains "==ERROR:"
            if "==ERROR:" in line:
                description = line.find("Sanitizer:")+11:]
                description.trim()
                self.description = description.split(' ')[0]

        self.stack = []
        if has_strack_trace():
            # line number and frame-number
            lno = 0
            fno = 0

            while "#0" not in lines[lno]:
                lno += 1

            while "#%d" % fno in lines[lno]:
                words = lines[lno].strip().split(' ')

                # function name is 4th word
                fname = words[3]

                # location is 5th word
                location = words[5]
                stack.append((fname, location))
                lno += 1
                fno += 1


