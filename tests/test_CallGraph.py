import unittest

from macke.CallGraph import CallGraph


class TestCallGraph(unittest.TestCase):

    def test_candidates_for_symbolic_encapsulation_simple(self):
        bcfile = "./examples/divisible.bc"
        c = CallGraph(bcfile).get_candidates_for_symbolic_encapsulation()

        self.assertEqual(len(c), 6)

        self.assertTrue(
            c.index("divby5") < c.index("divby10") < c.index("divby30"))

        self.assertTrue(c.index("divby2") < c.index("divby6"))
        self.assertTrue(c.index("divby3") < c.index("divby6"))

    def test_candidates_for_symbolic_encapsulation_circle(self):
        bcfile = "./examples/doomcircle.bc"
        c = CallGraph(bcfile).get_candidates_for_symbolic_encapsulation()
        self.assertEqual(c, ['a', 'b', 'c'])

    def test_candidates_for_symbolic_encapsulation_small(self):
        bcfile = "./examples/small.bc"
        c = CallGraph(bcfile).get_candidates_for_symbolic_encapsulation()
        self.assertEqual(len(c), 3)
        self.assertTrue(c.index("f2") < c.index("f1"))
        self.assertTrue(c.index("f3") < c.index("f1"))

    def test_edges_for_call_chain_propagation_divisible(self):
        bcfile = "./examples/divisible.bc"
        c = CallGraph(bcfile).get_grouped_edges_for_call_chain_propagation()

        self.assertEqual(6, len([pair for run in c for pair in run]))

    def test_edges_for_call_chain_propagation_circle(self):
        bcfile = "./examples/doomcircle.bc"
        c = CallGraph(bcfile).get_grouped_edges_for_call_chain_propagation()

        self.assertEqual(c, [[('a', 'b')], [('b', 'c')], [('c', 'a')]])

    def test_edges_for_call_chain_propagation_small(self):
        bcfile = "./examples/small.bc"
        c = CallGraph(bcfile).get_grouped_edges_for_call_chain_propagation()

        self.assertEqual(c, [[('f1', 'f2'), ('f1', 'f3')]])
