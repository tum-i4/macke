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
from .Klee import execute_klee, execute_klee_targeted_search
from .llvm_wrapper import encapsulate_symbolic, prepend_error


class Macke:

    def __init__(self, bitcodefile, parentdir="/tmp/macke", quiet=False):
        # Only accept valid files and directory
        assert(path.isfile(bitcodefile))

        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # generate name of directory with all run results
        newdirname = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)

        # Generate the path for the bitcode directory
        self.bcdir = path.join(self.rundir, "bitcode")

        # Generate the filename for the copy of the program
        self.program_bc = path.join(self.rundir, "program.bc")

        # Internal counter for the number of klee runs
        self.kleecount = 0

        # Initialize some statistic counter
        self.testcases = 0
        self.errfunccount = 0
        self.errtotalcount = 0

        # Map of function -> [kleeruns triggering an error]
        self.errorkleeruns = {}

        # Setting quiet == True suppress all outputs
        self.quiet = quiet

    def get_next_klee_directory(self):
        self.kleecount += 1
        result = path.join(self.rundir, "klee-out-%d" % self.kleecount)
        return result

    def run_complete_analysis(self):
        self.run_initialization()
        self.run_phase_one()
        self.run_phase_two()
        self.run_finalization()

    def run_initialization(self):
        # Create an empty run directory with empty bitcode directory
        makedirs(self.bcdir)

        # Copy the unmodified bitcode file
        shutil.copy2(self.bitcodefile, self.program_bc)

        # TODO copy current git hash of macke
        # TODO copy config file
        # TODO add self.bitcodefile information

        # Print some information for the user
        self.qprint(
            "Start analysis of %s in %s" % (self.bitcodefile, self.rundir))

    def run_phase_one(self):
        # Generate a call graph
        self.callgraph = CallGraph(self.bitcodefile)

        # Fill a list of functions for the symbolic encapsulation
        tasks = self.callgraph.get_candidates_for_symbolic_encapsulation()

        self.qprint("Phase 1: %d of %d functions are suitable for symbolic "
                    "encapsulation" % (len(tasks), len(self.callgraph.graph)))

        # Create a parallel pool with a process for each cpu thread
        pool = Pool(THREADNUM)

        # Storage for all complete runs
        kleedones = []

        # TODO store mapping of KLEE out directory -> function analyzed in dir

        # Dispense the KLEE runs on the workers in the pool
        for function in tasks:
            pool.apply_async(thread_phase_one, (
                function, self.program_bc, self.bcdir,
                self.get_next_klee_directory()
            ), callback=kleedones.append)

        # close the pool after all KLEE runs registered
        pool.close()

        if not self.quiet:
            # Keeping track of the progress until everything is done
            bar = ProgressBar(max_value=len(tasks))
            while len(kleedones) != len(tasks):
                bar.update(len(kleedones))
                sleep(0.3)
            bar.update(len(kleedones))
            bar.finish()
        pool.join()

        self.register_passed_klee_runs(kleedones)

        self.qprint("Phase 1: Found %d errors spread over %d functions" %
                    (self.errtotalcount, self.errfunccount))

    def run_phase_two(self):
        # Get (caller,callee)-pairs grouped in serialized runs
        runs = self.callgraph.get_grouped_edges_for_call_chain_propagation()

        # Store old counter to calculate progress in phase two
        olderrfunccount = self.errfunccount

        # Calculate some statistics
        qualified = sum(len(run) for run in runs)
        total = sum(len(value["calls"])
                    for key, value in self.callgraph.graph.items()
                    if key != "null function")
        # TODO count also calls from main if flag is given
        self.qprint("Phase 2: %d of %d calls are suitable for error chain "
                    "propagation" % (qualified, total))

        bar = ProgressBar(max_value=qualified)
        skipped = 0

        # all pairs inside a run can be executed in parallel
        for run in runs:
            # Initialize the pool of workers
            pool = Pool(THREADNUM)
            # Storage for the result
            kleedones = []

            for (caller, callee) in run:
                if callee in self.errorkleeruns:
                    pool.apply_async(thread_phase_two, (
                        caller, callee, self.errorkleeruns[callee],
                        self.bcdir, self.get_next_klee_directory()
                    ), callback=kleedones.append)
                else:
                    skipped += 1
            pool.close()

            if not self.quiet:
                # Keeping track of the progress until everything is done
                while (len(kleedones) + skipped) != qualified:
                    bar.update(len(kleedones) + skipped)
                    sleep(0.3)
                bar.update(len(kleedones) + skipped)
                bar.finish()
            pool.join()

            # Store the klees with error for next runs
            self.register_passed_klee_runs(kleedones)

        # TODO run main if arguments for it are given

        self.qprint("Phase 2: %d additional KLEE analyses were started" %
                    (qualified - skipped))
        self.qprint("Phase 2: errors were propagated to %d previously not "
                    "affected functions" %
                    (self.errfunccount - olderrfunccount))

    def run_finalization(self):
        self.qprint("Summary: %d tests were generated with %d KLEE runs" %
                    (self.testcases, self.kleecount))
        self.qprint("Summary: %d errors were detected spread over %d "
                    "functions" % (self.errtotalcount, self.errfunccount))

    def qprint(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    def delete_directory(self):
        shutil.rmtree(self.rundir, ignore_errors=True)

    def register_passed_klee_runs(self, kleedones):
        for k in kleedones:
            self.register_passed_klee_run(k)

    def register_passed_klee_run(self, kleedone):
        # Just give it a shorter name
        k = kleedone

        # fill some counters
        self.testcases += k.testcount
        self.errfunccount += (
            k.errorcount != 0 and k.analyzedfunc not in self.errorkleeruns)
        self.errtotalcount += k.errorcount

        # store runs uncovering errors for phase two
        if k.errorcount != 0:
            if k.analyzedfunc in self.errorkleeruns:
                self.errorkleeruns[k.analyzedfunc].append(k.outdir)
            else:
                self.errorkleeruns[k.analyzedfunc] = [k.outdir]


def thread_phase_one(functionname, program_bc, bcdir, outdir):
    """
    This function is executed by the parallel processes in phase one
    """

    # Build filename for the new bcfile generated by symbolic encapsulation
    encapsulated_bcfile = path.join(bcdir, "sym-" + functionname + ".bc")

    # Generate a bcfile with symbolic encapsulation as main function
    encapsulate_symbolic(program_bc, functionname, encapsulated_bcfile)

    # Run KLEE on it
    # TODO add relevant flags
    return execute_klee(encapsulated_bcfile, functionname, outdir, [])


def thread_phase_two(caller, callee, errordirlist, bcdir, outdir):
    """
    This function is executed by the parallel processes in phase two
    """
    # TODO add relevant flags
    # TODO globalize file names sym-...bc and chain-...bc

    # Generate required file names
    source_bc = path.join(bcdir, "sym-%s.bc" % caller)
    # TODO comment: - are not allowed in c function name
    prepended_bc = path.join(bcdir, "chain-%s-%s.bc" % (caller, callee))

    # Prepend the error summaries
    prepend_error(source_bc, callee, errordirlist, prepended_bc)

    # And run klee on it
    return execute_klee_targeted_search(prepended_bc, caller, callee, outdir)
