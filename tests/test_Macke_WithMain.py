import unittest

from macke.Macke import Macke


class TestMackeWithMain(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile):
        m = Macke(bcfile, quiet=True,
                  flags_user=["--max-time=60"],
                  posixflags=["--sym-files", "1", "100"],
                  posix4main=['--sym-args', '1', '1', '2'])
        m.run_initialization()
        m.run_phase_one()
        m.run_phase_two()
        m.delete_directory()
        return m

    def test_with_justmain(self):
        m = self.run_macke_test_on_file("examples/justmain.bc")

        self.assertEqual(m.testcases, 2)
        self.assertEqual(m.errtotalcount, 1)
        self.assertEqual(m.errfunccount, 1)

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc")

        self.assertEqual(m.errfunccount, 5)

        # The longest chain has goes through all functions including main
        self.assertEqual(len(m.errorchains[0]), 5)
