import unittest

from macke.Macke import Macke


class TestMackePhaseOne(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile):
        m = Macke(bcfile, quiet=True, flags_user=["--max-time=60"])
        m.run_initialization()
        m.run_phase_one()
        m.delete_directory()
        return m

    def test_with_divisible(self):
        m = self.run_macke_test_on_file("examples/divisible.bc")

        self.assertEqual(m.testcases, 10)
        self.assertEqual(m.errtotalcount, 0)
        self.assertEqual(m.errfunccount, 0)

        # All entries in the map should be empty
        self.assertEqual(sum(len(v) for _, v in m.errorkleeruns.items()), 0)

    def test_with_one_asserts(self):
        m = self.run_macke_test_on_file("examples/not42.bc")

        self.assertEqual(m.testcases, 2)
        self.assertEqual(m.errtotalcount, 1)
        self.assertEqual(m.errfunccount, 1)

        self.assertEqual(len(m.errorkleeruns), 1)
        self.assertEqual(len(m.errorkleeruns['not42']), 1)

    def test_main_generates_no_testcases(self):
        m = self.run_macke_test_on_file("examples/main.bc")

        self.assertEqual(m.testcases, 0)
        self.assertEqual(m.errtotalcount, 0)
        self.assertEqual(m.errfunccount, 0)

        self.assertEqual(m.errorkleeruns, {})

    def test_with_several_asserts(self):
        m = self.run_macke_test_on_file("examples/small.bc")

        # 2 for f2, 3 for f3 and sum of both for f1
        self.assertEqual(m.testcases, 10)
        # 3 for f1, 1 for f2, 2 for f3
        self.assertEqual(m.errtotalcount, 6)
        self.assertEqual(m.errfunccount, 3)

        self.assertEqual(len(m.errorkleeruns), 3)
        self.assertEqual(len(m.errorkleeruns['f1']), 1)
        self.assertEqual(len(m.errorkleeruns['f2']), 1)
        self.assertEqual(len(m.errorkleeruns['f3']), 1)
