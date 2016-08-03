import unittest

from macke import llvm_wrapper


class TestLLVMWrapper(unittest.TestCase):

    def test_extract_callgraph(self):
        json = llvm_wrapper.extract_callgraph("./examples/divisible.bc")
        # Just a view asserts - correct callgraph is tested in pass repo
        self.assertIn("main", json)
        self.assertIn("divby5", json)
        self.assertIn("divby10", json)
