import unittest

from macke.Macke import Macke


class TestMackePhaseTwo(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile):
        m = Macke(bcfile, quiet=True, flags_user=["--max-time=60"])
        m.run_initialization()
        m.run_phase_one()
        m.run_phase_two()
        m.delete_directory()
        return m

    def test_with_small(self):
        m = self.run_macke_test_on_file("examples/small.bc")

        self.assertEqual(m.errfunccount, 3)

        # All three asserts should be propagated - and no other error
        self.assertEqual(len(m.errorchains), 3)
        self.assertEqual(len(m.errorchains[0]), 2)
        self.assertEqual(len(m.errorchains[1]), 2)
        self.assertEqual(len(m.errorchains[2]), 2)

        # 3 for phase one, 2 in f1 for phase two
        self.assertEqual(len(m.errorkleeruns), 3)
        self.assertEqual(len(m.errorkleeruns['f1']), 3)
        self.assertEqual(len(m.errorkleeruns['f2']), 1)
        self.assertEqual(len(m.errorkleeruns['f3']), 1)

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc")

        self.assertEqual(m.errfunccount, 4)

        # The longest chain has goes through all functions
        self.assertTrue(m.errorchains)
        self.assertEqual(len(m.errorchains[0]), 4)
        # Their is only one chain with this length
        self.assertTrue(len(m.errorchains) == 1 or len(m.errorchains[1]) < 4)

        self.assertEqual(len(m.errorkleeruns), 4)
        self.assertEqual(len(m.errorkleeruns['c1']), 2)
        self.assertEqual(len(m.errorkleeruns['c2']), 2)
        self.assertEqual(len(m.errorkleeruns['c3']), 2)
        self.assertEqual(len(m.errorkleeruns['c4']), 1)
