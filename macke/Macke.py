"""
Main container for all steps of the MACKE analysis
"""

from datetime import datetime
import json
from multiprocessing import Pool
from progressbar import ProgressBar
from os import makedirs, path, symlink, remove
import shutil
import sys
from time import sleep
from .CallGraph import CallGraph
from .config import CONFIGFILE, THREADNUM, get_current_git_hash
from .Klee import execute_klee, execute_klee_targeted_search
from .llvm_wrapper import (
    encapsulate_symbolic, prepend_error, remove_unreachable_from)


class Macke:

    def __init__(self, bitcodefile, comment="",
                 parentdir="/tmp/macke", quiet=False,
                 flags_user=None, flags4main=None):
        # Only accept valid files and directory
        assert(path.isfile(bitcodefile))

        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile

        # Store information from command line
        self.comment = comment
        self.flags_user = flags_user if flags_user is not None else []
        self.flags4main = flags4main if flags4main is not None else []

        # generate name of directory with all run results
        self.starttime = datetime.now()
        newdirname = self.starttime.strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)
        self.parentdir = parentdir

        # Generate the path for the bitcode directory
        self.bcdir = path.join(self.rundir, "bitcode")

        # Generate the filename for the copy of the program
        self.program_bc = path.join(self.bcdir, "program.bc")
        self.symmains_bc = path.join(self.bcdir, "symmains.bc")

        # Generate the directory containing all klee runs
        self.kleedir = path.join(self.rundir, "klee")

        # Filename, where the index of the klee runs is stored
        self.kleejson = path.join(self.rundir, "klee.json")

        # Internal counter for the number of klee runs
        self.kleecount = 0

        # Initialize some statistic counter
        self.testcases = 0
        self.errfunccount = 0
        self.errtotalcount = 0

        # Map of function -> [kleeruns triggering an error]
        self.errorkleeruns = {}

        # Information about the error chains
        self.errorchains = dict()
        self.errorchainheads = set()

        # Setting quiet == True suppress all outputs
        self.quiet = quiet

    def get_next_klee_directory(self, info):
        self.kleecount += 1
        result = path.join(self.kleedir, "klee-out-%d" % self.kleecount)

        # Add the new file also to the klee index
        outjson = dict()
        outjson[result] = info
        with open(self.kleejson, 'a') as f:
            # Prepend separator for all but the first entry
            if self.kleecount != 1:
                f.write(", ")
            f.write(json.dumps(outjson)[1:-1])

        return result

    def run_complete_analysis(self):
        self.run_initialization()
        self.run_phase_one()
        self.run_phase_two()
        self.run_finalization()

    def run_initialization(self):
        # Create an some empty directories
        makedirs(self.bcdir)
        makedirs(self.kleedir)

        # Copy the unmodified bitcode file
        shutil.copy2(self.bitcodefile, self.program_bc)

        # Copy macke's config file
        shutil.copy2(CONFIGFILE, self.rundir)

        # Store some basic information about the current run
        with open(path.join(self.rundir, "info.json"), 'w') as f:
            info = dict()
            info["macke-git-version-hash"] = get_current_git_hash()
            info["analyzed-bitcodefile"] = path.abspath(self.bitcodefile)
            info["run-argv"] = sys.argv
            info["comment"] = self.comment
            json.dump(info, f)

        # Initialize a file for klee directory mapping
        with open(self.kleejson, 'w') as f:
            f.write("{")

        # Print some information for the user
        self.qprint(
            "Start analysis of %s in %s" % (self.bitcodefile, self.rundir))

    def run_phase_one(self):
        # Generate a call graph
        self.callgraph = CallGraph(self.bitcodefile)

        # Fill a list of functions for the symbolic encapsulation
        tasks = self.callgraph.get_candidates_for_symbolic_encapsulation(
            removemain=not bool(self.flags4main))

        self.qprint("Phase 1: %d of %d functions are suitable for symbolic "
                    "encapsulation" % (len(tasks), len(self.callgraph.graph)))

        # Copy the program bc before encapsulating everything symbolically
        shutil.copy2(self.program_bc, self.symmains_bc)

        # Generate one bcfile with symbolic encapsulations for each function
        for functionname in tasks:
            if functionname != "main":
                encapsulate_symbolic(self.symmains_bc, functionname)

        bar = ProgressBar(max_value=len(tasks)) if not self.quiet else None
        self.__execute_in_parallel_threads(tasks, 1, bar)

        if not self.quiet:
            bar.finish()

        self.qprint("Phase 1: Found %d errors spread over %d functions" %
                    (self.errtotalcount, self.errfunccount))

    def run_phase_two(self):
        # Get (caller,callee)-pairs grouped in serialized runs
        runs = self.callgraph.get_grouped_edges_for_call_chain_propagation(
            removemain=not bool(self.flags4main))

        # Store old counter to calculate progress in phase two
        olderrfunccount = self.errfunccount

        # Calculate some statistics
        qualified = sum(len(run) for run in runs)
        total = sum(len(value["calls"])
                    for key, value in self.callgraph.graph.items()
                    if key != "null function")

        self.qprint("Phase 2: %d of %d calls are suitable for error chain "
                    "propagation" % (qualified, total))

        totallyskipped = 0
        bar = ProgressBar(max_value=qualified) if not self.quiet else None

        for run in runs:
            # all pairs inside a run can be executed in parallel
            totallyskipped += self.__execute_in_parallel_threads(run, 2, bar)

        if not self.quiet:
            bar.finish()

        self.errorchains = self.reconstruct_error_chains()

        self.qprint("Phase 2: %d additional KLEE analyses were started" %
                    (qualified - totallyskipped))
        self.qprint("Phase 2: %d error-chains were found through %d "
                    "previously not affected functions" %
                    (len(self.errorchains),
                     self.errfunccount - olderrfunccount))
        # TODO add number of chains from main

    def run_finalization(self):
        self.endtime = datetime.now()

        self.qprint("Summary: %d tests were generated with %d KLEE runs" %
                    (self.testcases, self.kleecount))
        self.qprint("Summary: %d errors were detected spread over %d "
                    "functions" % (self.errtotalcount, self.errfunccount))

        # Close the json of the klee run index file
        with open(self.kleejson, 'a') as f:
            f.write("}")

        # Export all the data gathered so far to a json file
        with open(path.join(self.rundir, "result.json"), 'w') as f:
            info = dict()

            info["start"] = self.starttime.isoformat()
            info["end"] = self.endtime.isoformat()
            info["testcases"] = self.testcases
            info["numberOfFunctionsWithErrors"] = self.errfunccount
            info["totalNumberOfErrors"] = self.errtotalcount
            info["functionToKleeRunWithErrorMap"] = self.errorkleeruns
            info["errorchains"] = self.errorchains

            json.dump(info, f)

        # link the current directory as macke-last
        symlinkname = path.join(self.parentdir, "macke-last")
        try:
            remove(symlinkname)
        except OSError:
            pass
        symlink(self.rundir, symlinkname)

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

        if phase == 1:
            for function in run:
                pool.apply_async(thread_phase_one, (
                    function, self.symmains_bc, self.bcdir,
                    self.get_next_klee_directory(
                        dict(phase=phase, function=function)),
                    self.flags_user, self.flags4main
                ), callback=callbacklist.append)
            # You cannot skip anything in phase one -> 0 skips
        elif phase == 2:
            for (caller, callee) in run:
                if callee in self.errorkleeruns:
                    pool.apply_async(thread_phase_two, (
                        caller, callee, self.symmains_bc,
                        self.errorkleeruns[callee], self.bcdir,
                        self.get_next_klee_directory(
                            dict(phase=phase, caller=caller, callee=callee)),
                        self.flags_user, self.flags4main
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

        # All new errors are potential heads of error chains
        for errfile in k.errfiles:
            self.errorchainheads.add(errfile)

        # store all error chains
        for new, old in k.chained:
            self.errorchains[new] = old
            # the old error is no longer a head
            if old in self.errorchainheads:
                self.errorchainheads.remove(old)

    def reconstruct_error_chains(self):
        result = []

        for head in self.errorchainheads:
            chain = [head]
            probe = head
            while probe in self.errorchains:
                probe = self.errorchains[probe]
                chain.append(probe)
            if len(chain) > 1:
                result.append(chain)

        # Longest chains are reported first
        result.sort(key=lambda x: (len(x), x[0]), reverse=True)
        return result


def get_error_chain_bcfile(bcdir, caller, callee):
    # "-" is a good separator, because "-" is not allowed in c function names
    return path.join(bcdir, "chain-%s-%s.bc" % (caller, callee))


def thread_phase_one(
        functionname, symmains_bc, bcdir, outdir, flags, flags4main):
    """
    This function is executed by the parallel processes in phase one
    """
    # Just run KLEE on it
    return execute_klee(symmains_bc, functionname, outdir, flags, flags4main)


def thread_phase_two(caller, callee, symmains_bc, errordirlist, bcdir,
                     outdir, flags, flags4main):
    """
    This function is executed by the parallel processes in phase two
    """
    # Generate required file name
    prepended_bc = get_error_chain_bcfile(bcdir, caller, callee)

    # Prepend the error summaries
    prepend_error(symmains_bc, callee, errordirlist, prepended_bc)

    # And remove all code, that is unreachable during analysis
    entrypoint = "macke_%s_main" % caller if caller != "main" else "main"
    remove_unreachable_from(entrypoint, prepended_bc)

    # And run klee on it
    return execute_klee_targeted_search(
        prepended_bc, caller, callee, outdir, flags, flags4main)
