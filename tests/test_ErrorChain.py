import unittest

from macke.Macke import Macke
from macke.ErrorChain import reconstruct_all_error_chains


class TestErrorChain(unittest.TestCase):

    def run_macke_test_on_file(self, bcfile):
        m = Macke(bcfile, quiet=True,
                  flags_user=["--max-time=60"],
                  posix4main=['--sym-args', '1', '1', '2'])
        m.run_initialization()
        m.run_phase_one()
        m.run_phase_two()
        m.delete_directory()
        return m

    def test_with_chain(self):
        m = self.run_macke_test_on_file("examples/chain.bc")
        chains = reconstruct_all_error_chains(m.errorregistry, m.callgraph)

        # Only one reason for the chain
        self.assertEqual(len(chains), 1)

        # Only one chain trough all functions
        self.assertEqual(
            next(iter(chains.values())), [['c4', 'c3', 'c2', 'c1', 'main']])

    def test_with_split(self):
        m = self.run_macke_test_on_file("examples/split.bc")
        chains = reconstruct_all_error_chains(m.errorregistry, m.callgraph)

        # All errors share the same vulnerable instruction
        self.assertEqual(len(chains), 1)

        # Two chains to top
        self.assertEqual(
            next(iter(chains.values())),
            [['bottom', 'left', 'top'], ['bottom', 'right', 'top']])

    def test_with_small(self):
        m = self.run_macke_test_on_file("examples/small.bc")
        chains = reconstruct_all_error_chains(m.errorregistry, m.callgraph)

        self.assertEqual(len(chains), 3)

        for vulninst, chainlist in chains.items():
            if vulninst.endswith("small.c:4"):
                self.assertEqual(chainlist, [['f2', 'f1']])
            elif vulninst.endswith("small.c:9"):
                self.assertEqual(chainlist, [['f3', 'f1']])
            elif vulninst.endswith("small.c:10"):
                self.assertEqual(chainlist, [['f3', 'f1']])
            else:
                raise Exception("Unexpected vulnerable instruction")

    def test_with_sanatized(self):
        m = self.run_macke_test_on_file("examples/sanatized.bc")
        chains = reconstruct_all_error_chains(m.errorregistry, m.callgraph)

        self.assertEqual(len(chains), 1)
        self.assertEqual(next(iter(chains.values())), [['c4', 'c3']])
