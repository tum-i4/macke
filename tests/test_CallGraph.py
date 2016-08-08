import unittest

from macke.CallGraph import CallGraph


def generate_CallGraph_from_file(bcfile):
    return CallGraph(bcfile).get_candidates_for_symbolic_encapsulation()


class TestCallGraph(unittest.TestCase):

    def test_candidates_for_symbolic_encapsulation_simple(self):
        c = generate_CallGraph_from_file("./examples/divisible.bc")

        self.assertEqual(len(c), 6)

        self.assertTrue(
            c.index("divby5") < c.index("divby10") < c.index("divby30"))

        self.assertTrue(c.index("divby2") < c.index("divby6"))
        self.assertTrue(c.index("divby3") < c.index("divby6"))

    def test_candidates_for_symbolic_encapsulation_circle(self):
        c = generate_CallGraph_from_file("./examples/doomcircle.bc")
        self.assertEqual(c, ['a', 'b', 'c'])
