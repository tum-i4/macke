import unittest

from macke.Macke import Macke


class TestMackePhaseOne(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile):
        m = Macke(bcfile, quiet=True)
        m.run_initialization()
        m.run_phase_one()
        m.run_phase_two()
        m.delete_directory()
        return m

    def test_with_small(self):
        m = self.run_macke_test_on_file("examples/small.bc")

        self.assertEqual(m.errfunccount, 3)

        chains = m.reconstruct_error_chains()
        # All three asserts should be propagated
        self.assertEqual(len(chains[0]), 2)
        self.assertEqual(len(chains[1]), 2)
        self.assertEqual(len(chains[2]), 2)
        # And no other error
        self.assertEqual(len(chains), 3)

        # 3 for phase one, 2 in f1 for phase two
        self.assertEqual(len(m.errorkleeruns), 3)
        self.assertEqual(len(m.errorkleeruns['f1']), 3)
        self.assertEqual(len(m.errorkleeruns['f2']), 1)
        self.assertEqual(len(m.errorkleeruns['f3']), 1)

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc")

        self.assertEqual(m.errfunccount, 4)

        # The longest chain has goes through all functions
        chains = m.reconstruct_error_chains()
        self.assertEqual(len(chains[0]), 4)
        # Their is only one chain with this length
        self.assertTrue(len(chains) == 1 or len(chains[1]) < 4)

        self.assertEqual(len(m.errorkleeruns), 4)
        self.assertEqual(len(m.errorkleeruns['c1']), 2)
        self.assertEqual(len(m.errorkleeruns['c2']), 2)
        self.assertEqual(len(m.errorkleeruns['c3']), 2)
        self.assertEqual(len(m.errorkleeruns['c4']), 1)
