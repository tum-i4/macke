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

    def test_with_divisible(self):
        m = self.run_macke_test_on_file("examples/small.bc")

        # TODO no idea about the first two numbers, rethink it
        # after the correct flags were added
        # self.assertEqual(m.testcases, 21)
        # self.assertEqual(m.errtotalcount, 13)
        self.assertEqual(m.errfunccount, 3)

        # 3 for phase one, 2 in f1 for phase two
        self.assertEqual(len(m.errorkleeruns), 3)
        self.assertEqual(len(m.errorkleeruns['f1']), 3)
        self.assertEqual(len(m.errorkleeruns['f2']), 1)
        self.assertEqual(len(m.errorkleeruns['f3']), 1)

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc")

        # TODO no idea about the first two numbers, rethink it
        # after the correct flags were added
        # self.assertEqual(m.testcases, 23)
        # self.assertEqual(m.errtotalcount, 16)
        self.assertEqual(m.errfunccount, 4)

        self.assertEqual(len(m.errorkleeruns), 4)
        self.assertEqual(len(m.errorkleeruns['c1']), 2)
        self.assertEqual(len(m.errorkleeruns['c2']), 2)
        self.assertEqual(len(m.errorkleeruns['c3']), 2)
        self.assertEqual(len(m.errorkleeruns['c4']), 1)
