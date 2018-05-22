

class StackTrace:
    def __init__(self, stack, entryfunc):
        # Store the entry func, this is needed for prepending a stack
        self.entryfunction = entryfunc

        self.entryFrame = 0
        for (fname, _) in stack:
            if fname == entryfunc:
                break
            self.entryFrame += 1

        self.stack = stack[:self.entryFrame + 1]


    def __eq__(self, other):
        return self.stack == other.stack

    def __str__(self):
        return str(self.stack)

    def is_contained_in(self, other):
        slen = len(self.stack)
        olen = len(other.stack)
        if slen >= olen:
            return False

        for i in range(slen):
            if self.stack[i] != other.stack[i]:
                return False
        return True


    def prepend(self, other):
        """
        Prepend the other stacktrace to self
        This function assumes, that the self stack has a call to other.entryfunction
        It looks for this call this frame and all lower frames with the ones in other
        """

        call_pos = 0
        for (fname, _) in self.stack:
            if fname == other.entryfunction:
                break
            call_pos += 1

        old_stack = self.stack
        self.stack = other.stack[:other.entryFrame + 1] + self.stack[call_pos + 1:] 
