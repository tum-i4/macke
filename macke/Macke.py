"""
Main container for all steps of the MACKE analysis
"""

from os import makedirs, path
from datetime import datetime
import shutil
from .CallGraph import CallGraph
from .llvm_wrapper import extract_callgraph


class Macke:

    def __init__(self, bitcodefile, parentdir="/tmp/macke"):
        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # generate name of directory with all run results
        newdirname = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)

    def run_complete_analysis(self):
        self.run_initialization()
        self.run_phase_one()
        self.run_phase_two()

    def run_initialization(self):
        # Create an empty run directory with empty bitcode directory
        makedirs(path.join(self.rundir, "bitcode"))

        # Copy the unmodified bitcode file
        shutil.copy2(self.bitcodefile, path.join(self.rundir, "program.bc"))

        # TODO copy current git hash of macke
        # TODO copy config file

        # Print some information for the user
        print("Start analysis of %s in %s" % (self.bitcodefile, self.rundir))

    def run_phase_one(self):
        # Generate a call graph
        self.callgraph = CallGraph(extract_callgraph(self.bitcodefile))

        # Fill a list of functions for the symbolic encapsulation
        tasks = self.callgraph.get_candidates_for_symbolic_encapsulation()

        # Copy the original file for symbolic encapsulation
        shutil.copy2(
            self.bitcodefile,
            path.join(self.rundir, "bitcode", "encapsulated.bc")
        )

        for task in tasks:
            print("TODO encapsulate", task)

    def run_phase_two(self):
        pass
