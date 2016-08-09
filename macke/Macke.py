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

        bar = ProgressBar(max_value=len(tasks)) if not self.quiet else None
        self.__execute_in_parallel_threads(tasks, 1, bar)

        if not self.quiet:
            bar.finish()

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

        totallyskipped = 0
        bar = ProgressBar(max_value=qualified) if not self.quiet else None

        for run in runs:
            # all pairs inside a run can be executed in parallel
            totallyskipped += self.__execute_in_parallel_threads(run, 2, bar)

        if not self.quiet:
            bar.finish()

        # TODO run main if arguments for it are given

        self.qprint("Phase 2: %d additional KLEE analyses were started" %
                    (qualified - totallyskipped))
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

    def __execute_in_parallel_threads(self, run, phase, pbar):
        assert(phase == 1 or phase == 2)

        if not self.quiet:
            # Store the state of the progressbar before running anything
            donebefore = pbar.value if pbar is not None else 0

        # Create a pool with a fixed number of parallel processes
        # Either use the configured number of thread or one for each cpu thread
        pool = Pool(THREADNUM)
        # Storage for the result of the runs
        kleedones = []

        # Dispense the KLEE runs on the workers in the pool
        skipped = self.__put_phase_threads_into_pool(
            phase, pool, run, kleedones)

        # close the pool after all KLEE runs are registered
        pool.close()

        if not self.quiet:
            # Keeping track of the progress until everything is done
            while (len(kleedones) + skipped) != len(run):
                pbar.update(donebefore + len(kleedones) + skipped)
                sleep(0.3)
            # One final update
            pbar.update(donebefore + len(kleedones) + skipped)

        # At this point, all threads must be finished
        pool.join()

        # Store the klees with error for next runs
        self.register_passed_klee_runs(kleedones)

        return skipped

    def __put_phase_threads_into_pool(self, phase, pool, run, callbacklist):
        assert(phase == 1 or phase == 2)

        skipped = 0

        # TODO store mapping of KLEE out directory -> function analyzed in dir

        if phase == 1:
            for function in run:
                pool.apply_async(thread_phase_one, (
                    function, self.program_bc, self.bcdir,
                    self.get_next_klee_directory()
                ), callback=callbacklist.append)
            # You cannot skip anything in phase one -> 0 skips
        elif phase == 2:
            for (caller, callee) in run:
                if callee in self.errorkleeruns:
                    pool.apply_async(thread_phase_two, (
                        caller, callee, self.errorkleeruns[callee],
                        self.bcdir, self.get_next_klee_directory()
                    ), callback=callbacklist.append)
                else:
                    skipped += 1
        return skipped

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


def get_symbolic_encapsulated_bcfile(bcdir, functionname):
    return path.join(bcdir, "sym-%s.bc" % functionname)


def get_error_chain_bcfile(bcdir, caller, callee):
    # "-" is a good separator, because "-" is not allowed in c function names
    return path.join(bcdir, "chain-%s-%s.bc" % (caller, callee))


def thread_phase_one(functionname, program_bc, bcdir, outdir):
    """
    This function is executed by the parallel processes in phase one
    """

    # Build filename for the new bcfile generated by symbolic encapsulation
    encapsulated_bcfile = get_symbolic_encapsulated_bcfile(bcdir, functionname)

    # Generate a bcfile with symbolic encapsulation as main function
    encapsulate_symbolic(program_bc, functionname, encapsulated_bcfile)

    # Run KLEE on it
    # TODO add relevant flags
    return execute_klee(encapsulated_bcfile, functionname, outdir, [])


def thread_phase_two(caller, callee, errordirlist, bcdir, outdir):
    """
    This function is executed by the parallel processes in phase two
    """

    # Generate required file names
    source_bc = get_symbolic_encapsulated_bcfile(bcdir, caller)
    prepended_bc = get_error_chain_bcfile(bcdir, caller, callee)

    # Prepend the error summaries
    prepend_error(source_bc, callee, errordirlist, prepended_bc)

    # And run klee on it
    # TODO add relevant flags
    return execute_klee_targeted_search(prepended_bc, caller, callee, outdir)
