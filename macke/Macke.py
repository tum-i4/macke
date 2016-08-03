"""
Main container for all steps of the MACKE analysis
"""

from datetime import datetime
from multiprocessing import Pool
from progressbar import ProgressBar
from os import makedirs, path
import shutil
from time import sleep
from .CallGraph import CallGraph
from .config import THREADNUM
from .Klee import KleeRound
from .llvm_wrapper import encapsulate_symbolic


class Macke:

    def __init__(self, bitcodefile, parentdir="/tmp/macke"):
        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # generate name of directory with all run results
        newdirname = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)

        # store the path for the bitcode file with all encapsulations
        self.encapsulated_bcfile = path.join(
            self.rundir, "bitcode", "encapsulated.bc")

        # Internal counter for the number of klee runs
        self.kleecount = 1

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
        # TODO add self.bitcodefile information

        # Print some information for the user
        print("Start analysis of %s in %s" % (self.bitcodefile, self.rundir))

    def run_phase_one(self):
        # Generate a call graph
        self.callgraph = CallGraph(self.bitcodefile)

        # Fill a list of functions for the symbolic encapsulation
        tasks = self.callgraph.get_candidates_for_symbolic_encapsulation()

        print("Phase 1: %d of %d functions are suitable for symbolic "
              "encapsulation" % (len(tasks), len(self.callgraph.graph)))

        # Copy the original file for symbolic encapsulation
        shutil.copy2(self.bitcodefile, self.encapsulated_bcfile)

        # Lists of KleeRounds in phase one
        kleetodos = []
        kleedones = []

        # Encapsulate all suitable functions symbolically
        for function in tasks:
            encapsulate_symbolic(self.encapsulated_bcfile, function)
            kleetodos.append(self.prepare_phase_one_klee(function))

        # Create a parallel pool with a process for each cpu thread
        pool = Pool(THREADNUM)

        # Dispense the KLEE runs on the workers in the pool
        for k in kleetodos:
            pool.apply_async(thread_phase_one, (k,), callback=kleedones.append)
        # close the pool after all KLEE runs registered before
        pool.close()

        # Keeping track of the progress until everything is done
        with ProgressBar(max_value=len(kleetodos)) as bar:
            while len(kleedones) != len(kleetodos):
                bar.update(len(kleedones))
                sleep(0.3)
            bar.update(len(kleedones))

        # initialize some counters
        errfunc, errtotal, testcases = 0, 0, 0

        for k in kleedones:
            errfunc += 1 if k.does_contains_errors() else 0
            c, t = k.get_statistics()
            testcases += c
            errtotal += t
            # TODO prepare them for phase two

        print("Phase 1: %d test cases generated. "
              "Found %d total errors in %d functions" %
              (testcases, errtotal, errfunc))

    def prepare_phase_one_klee(self, encapsulated):
        """
        Prepare a KLEE round for phase one, that is executed later
        """
        result = KleeRound(
            self.encapsulated_bcfile,
            path.join(self.rundir, "klee-out-%d" % self.kleecount),
            [],  # TODO add relevant flags
            "macke_%s_main" % encapsulated
        )
        self.kleecount += 1
        return result

    def run_phase_two(self):
        print("Phase 2: ... is not working ... yet ^^")


def thread_phase_one(klee):
    """
    This function is executed by the parallel processes in phase one
    """
    klee.run()
    return klee
