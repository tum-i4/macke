import unittest

from macke import llvm_wrapper, CallGraph


class TestLLVMWrapper(unittest.TestCase):

    def test_candidates_for_symbolic_encapsulation(self):
        # Generate call graph from file
        json = llvm_wrapper.extract_callgraph("./examples/divisible.bc")
        canditates = CallGraph.CallGraph(
            json).get_candidates_for_symbolic_encapsulation()

        # Check total length
        self.assertEqual(len(canditates), 6)

        # Depest level
        self.assertEqual(canditates[0], "divby5")

        # 3rd level
        self.assertEqual(
            sorted(canditates[1:4]), ["divby10", "divby2", "divby3"])

        # 2nd leven
        self.assertEqual(
            sorted(canditates[4:6]), ["divby30", "divby6"])
