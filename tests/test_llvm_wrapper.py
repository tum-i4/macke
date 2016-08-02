import unittest

from macke import llvm_wrapper, CallGraph


class TestLLVMWrapper(unittest.TestCase):

    def test_extract_callgraph(self):
        json = llvm_wrapper.extract_callgraph("./examples/divisible.bc")
        cg = CallGraph.CallGraph(json)
        # Just a view asserts - correct callgraph is tested in pass repo
        self.assertIn("main", cg)
        self.assertIn("divby5", cg)
        self.assertIn("divby10", cg)
