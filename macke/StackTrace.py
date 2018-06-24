

class StackTrace:
    def __init__(self, stack, entryfunc):
        # Store the entry func, this is needed for prepending a stack
        self.entryfunction = entryfunc

        self.entryFrame = 0
        self.stack = []
        for (fname, loc) in stack:
            if '.' in fname:
                fname = fname[:fname.index('.')]
            self.stack.append((fname, loc))
            if fname == entryfunc:
                break
            self.entryFrame += 1


    def __eq__(self, other):
        return self.stack == other.stack

    def __str__(self):
        return str(self.stack)

    def is_contained_in(self, other):
        slen = len(self.stack)
        olen = len(other.stack)
        if slen > olen:
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

        old_stack = self.stack
        self.stack = other.stack[:other.entryFrame + 1] + self.stack 


    def get_depth(self):
        return len(self.stack)

    def get_indices(self):
        """
        Return a list of (depth, function, location), representing each entry
        This tuple can be hashed to find possible candidates
        Note, that the last call has depth 0, so that it does not change,
        when prepending stacktraces
        """
        ret = []
        cur_depth = 0
        for (func, loc) in self.stack:
            ret.append((cur_depth, func, loc))
            cur_depth += 1
        assert(cur_depth == self.get_depth())
        return ret


    def get_head(self):
        return self.stack[-1]

    def get_head_index(self):
        func, loc = self.get_head()
        depth = self.get_depth()
        return (depth - 1, func, loc)
