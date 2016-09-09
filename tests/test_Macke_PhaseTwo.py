import unittest

from macke.Macke import Macke


class TestMackePhaseTwo(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile, excludes_in_phase_two):
        m = Macke(
            bcfile, quiet=True, flags_user=["--max-time=60"],
            exclude_known_from_phase_two=excludes_in_phase_two)
        m.run_initialization()
        m.run_phase_one()
        m.run_phase_two()
        m.delete_directory()
        return m

    def test_with_small(self):
        m = self.run_macke_test_on_file("examples/small.bc", False)

        self.assertEqual(m.errorregistry.count_functions_with_errors(), 3)

        # Check, that all three errors were prepended and triggered again
        for vulninst in ["small.c:4", "small.c:9", "small.c:10"]:
            self.assertTrue(any(
                err.vulnerable_instruction.endswith(vulninst) and
                err.errfile.endswith(".macke.err")
                for err in m.errorregistry.forfunction["f1"]),
                "Missing %s" % vulninst)

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc", False)

        self.assertEqual(m.errorregistry.count_functions_with_errors(), 4)

        rooterror = m.errorregistry.forfunction['c4'][0]

        oldchainheads = [rooterror]
        for i in range(1, 4):
            newchainheads = list()
            for error in oldchainheads:
                newchainheads.extend(
                    m.errorregistry.mackeforerrfile[error.errfile])
            oldchainheads = newchainheads[:]
            self.assertTrue(oldchainheads, "Iteration %d failed" % i)
        self.assertEqual(oldchainheads[0].entryfunction, "c1")

    def test_with_sanatized(self):
        m = self.run_macke_test_on_file("examples/sanatized.bc", True)

        self.assertEqual(m.errorregistry.count_functions_with_errors(), 2)
        self.assertEqual(m.kleecount, 4 + 1)
