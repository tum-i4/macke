import unittest

from macke.CallGraph import CallGraph


class TestCallGraph(unittest.TestCase):

    def test_candidates_for_symbolic_encapsulation_simple(self):
        bcfile = "./examples/divisible.bc"
        c = CallGraph(bcfile).list_symbolic_encapsulable()

        self.assertEqual(len(c), 6)

        self.assertTrue(
            c.index("divby5") < c.index("divby10") < c.index("divby30"))

        self.assertTrue(c.index("divby2") < c.index("divby6"))
        self.assertTrue(c.index("divby3") < c.index("divby6"))

    def test_candidates_for_symbolic_encapsulation_circle(self):
        bcfile = "./examples/doomcircle.bc"
        c = CallGraph(bcfile).list_symbolic_encapsulable()
        self.assertEqual(c, ['a', 'b', 'c'])

    def test_candidates_for_symbolic_encapsulation_small(self):
        bcfile = "./examples/small.bc"
        c = CallGraph(bcfile).list_symbolic_encapsulable()
        self.assertEqual(len(c), 3)
        self.assertTrue(c.index("f2") < c.index("f1"))
        self.assertTrue(c.index("f3") < c.index("f1"))

    def test_edges_for_call_chain_propagation_divisible(self):
        bcfile = "./examples/divisible.bc"
        c = CallGraph(bcfile).group_independent_calls()

        self.assertEqual(6, len([pair for run in c for pair in run]))

        # This asserts are specifig to the grouping strategy
        # If you change the strategy, you probably have to change this
        self.assertEqual(c[0], [
            ('divby10', 'divby2'), ('divby10', 'divby5'),
            ('divby30', 'divby3'), ('divby6', 'divby2'), ('divby6', 'divby3')])
        self.assertEqual([('divby30', 'divby10')], c[1])

    def test_edges_for_call_chain_propagation_circle(self):
        bcfile = "./examples/doomcircle.bc"
        c = CallGraph(bcfile).group_independent_calls()

        self.assertEqual(c, [[('c', 'a')], [('a', 'b')], [('b', 'c')]])

    def test_edges_for_call_chain_propagation_small(self):
        bcfile = "./examples/small.bc"
        c = CallGraph(bcfile).group_independent_calls()

        self.assertEqual(c, [[('f1', 'f2'), ('f1', 'f3')]])

    def test_edges_for_call_chain_propagation_factorial(self):
        bcfile = "./examples/factorial.bc"
        c = CallGraph(bcfile).group_independent_calls()

        self.assertEqual(c, [[('fac', 'fac')]])
