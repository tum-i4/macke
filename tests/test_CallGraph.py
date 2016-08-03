import unittest

from macke import CallGraph


class TestLLVMWrapper(unittest.TestCase):

    def test_candidates_for_symbolic_encapsulation_simple(self):
        # Generate call graph from file
        bcfile = "./examples/divisible.bc"
        c = CallGraph.CallGraph(
            bcfile).get_candidates_for_symbolic_encapsulation()

        # Check total length
        self.assertEqual(len(c), 6)

        # Chain 1
        self.assertTrue(
            c.index("divby5") < c.index("divby10") < c.index("divby30"))

        self.assertTrue(c.index("divby2") < c.index("divby6"))
        self.assertTrue(c.index("divby3") < c.index("divby6"))

    def test_candidates_for_symbolic_encapsulation_circle(self):
        # Generate call graph from file
        bcfile = "./examples/doomcircle.bc"
        c = CallGraph.CallGraph(
            bcfile).get_candidates_for_symbolic_encapsulation()

        self.assertEqual(c, ['a', 'b', 'c'])
