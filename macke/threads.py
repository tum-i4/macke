"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager, FuzzResult
from .Logger import Logger, PlotDataLogger
from .read_klee_testcases import process_klee_out

import subprocess
import traceback
import sys
import glob
import time

# We parse the fuzztime in flags
def thread_fuzz_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, afl_to_klee_dir, fuzztime,
                          flipper_mode):
    Logger.log("thread_fuzz_phase_one: " + functionname + "\n", verbosity_level="debug")
    cgroup = cgroupqueue.get()
    try:
        result = fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, fuzztime, flipper_mode, afl_to_klee_dir)
        #result.convert_erros_to_klee_files(["queue", "crashes"])
        resultlist.append(result)
        Logger.log("thead_fuzz_phase_one: resultlist: %s\n"%(str(resultlist)))
    except Exception as exc:
        Logger.log("A fuzz thread in phase one threw an exception\n", verbosity_level="error")
        Logger.log("The analyzed function was: " + functionname + "\n", verbosity_level="error")
        Logger.log(exc + "\n", verbosity_level="error")
        Logger.log(sys.exc_info() + "\n", verbosity_level="error")
        Logger.log(str(traceback.format_tb(sys.exc_info()[2])) + "\n", verbosity_level="error")

    cgroupqueue.put(cgroup)

    Logger.log("done thread_fuzz_phase_one: " + functionname + "\n", verbosity_level="debug")

# Arguments a combination of thread_fuzz_phase_one and thread_phase_one (symbolic) plus flippertime
# We parse the fuzztime in flags
def thread_flipper_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, afl_to_klee_dir, fuzztime,
                             symmains_bc, klee_outdir, klee_timeout, flags, posixflags, posix4main, timeout, no_optimize=False,
                             flipper_mode=True, logging_desired=False
                             ):
    Logger.log("thread_flipper_phase_one: " + functionname + " (timeout " + str(timeout) + ")\n",
               verbosity_level="debug")

    progress_done = True
    klee_result = None
    fuzz_result = None

    flip_counter = 0

    timeout_timestamp = time.time() + timeout
    timeout_detected = False
    #afl_to_klee_dir = path.join(outdir, "afl_to_klee_dir") # macke_errors

    if logging_desired:
        Logger.log("Plotting data at " + outdir + "\n", verbosity_level="debug")
        plot_data_logger = PlotDataLogger(outdir, klee_outdir, outdir)
    else:
        Logger.log("Plotting data not desired\n", verbosity_level="debug")
        plot_data_logger = None

    while progress_done and (not timeout_detected):
        # TODO: in case of no progress, keep going until at least some progress is done?
        progress_done = False

        # Run klee
        Logger.log("trying klee on: " + functionname + "\n", verbosity_level="debug")

        time_remaining = timeout_timestamp - time.time()
        if time_remaining<0:
            timeout_detected = True
        
        if not timeout_detected:
            if flip_counter>0: # If this is not the first run of KLEE then count it as a flip
                flip_counter += 1
                Logger.log("Flipping!\n", verbosity_level="debug")
            try:
                klee_time = min([klee_timeout, time_remaining])
                klee_result = execute_klee(
                    symmains_bc, functionname, klee_outdir, klee_time, flipper_mode, flags, posixflags, posix4main,
                    no_optimize, afl_to_klee_dir, plot_data_logger)
            # pylint: disable=broad-except
            except Exception as exc:
                Logger.log("A thread in phase one threw an exception\n", verbosity_level="error")
                Logger.log("The analyzed function was: " + functionname + "\n", verbosity_level="error")
                Logger.log(exc + "\n", verbosity_level="error")
                Logger.log(sys.exc_info() + "\n", verbosity_level="error")
                Logger.log(str(traceback.extract_tb(sys.exc_info()[2])) + "\n", verbosity_level="error")

            # Translate klee files to fuzz files

            if klee_result:
                if klee_result.progress:
                    progress_done = True
                    Logger.log("KLEE has made progress (" + str(klee_result.progress) + ")\n", verbosity_level="info")
                    #argv = []
                    Logger.log("klee_outdir: " + klee_outdir + "\n", verbosity_level="debug")
                    #for k in glob.glob(klee_outdir + "/klee-*"):
                    #    argv.extend(process_klee_out(k, fuzzmanager.inputbasedir + "/input"))
                    try:
                        process_klee_out(klee_outdir, fuzzmanager.inputforfunc[functionname])
                    except Exception as e:
                        Logger.log("Unexpected error while processing klee output: %s\n"%(e), verbosity_level="error")
                        #sys.exit(1)
                    # argv = self.clean_argv(argv)
                    #Logger.log("argv: " + str(argv) + "\n", verbosity_level="debug")
                    #time.sleep(1)

                else:
                    Logger.log("KLEE has not made progress\n", verbosity_level="debug")


        time_remaining = timeout_timestamp - time.time()
        if time_remaining<0:
            timeout_detected = True
        if not timeout_detected:
            flip_counter += 1
            Logger.log("Flipping!\n", verbosity_level="debug")
            # Run fuzzer
            Logger.log("trying afl on: " + functionname + "\n", verbosity_level="debug")

            cgroup = cgroupqueue.get()
            try:
                afl_time = min([fuzztime, time_remaining])
                fuzz_result = fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, afl_time, flipper_mode,
                                                           afl_to_klee_dir, plot_data_logger)

            except Exception as exc:
                print()
                print("A fuzz thread in phase one throws an exception")
                print("The analyzed function was:", functionname)
                print(exc)
                print()
                print(sys.exc_info())
                traceback.print_tb(sys.exc_info()[2])
            cgroupqueue.put(cgroup)

            if fuzz_result:
                if fuzz_result.progress:
                    progress_done = True
                    # transform fuzz files to klee files
                    fuzz_result.convert_to_klee_files(fuzzmanager)
                    Logger.log("AFL has made progress (" + str(fuzz_result.progress) + ")\n", verbosity_level="info")
                else:
                    Logger.log("AFL has not made progress\n", verbosity_level="debug")

        if time.time() >= timeout_timestamp:
            Logger.log("Timeout detected\n", verbosity_level="debug")
            timeout_detected = True

    if fuzz_result:
        fuzz_result.convert_erros_to_klee_files(["queue", "crashes"])

    if not timeout_detected:
        # flipping terminated due to lack of progress
        # run KLEE for the remaining time

        remaining_time = timeout_timestamp - time.time()

        if remaining_time > 1:
            Logger.log("Running KLEE again for " + str(remaining_time) + "\n", verbosity_level="debug")
            try:
                # run KLEE without saturation checks, as flipping is no longer performed
                klee_result = execute_klee( symmains_bc, functionname, outdir, remaining_time, flipper_mode, flags,
                                            posixflags, posix4main, no_optimize)
            # pylint: disable=broad-except
            except Exception as exc:
                Logger.log("A thread in phase one threw an exception\n", verbosity_level="error")
                Logger.log("The analyzed function was: " + functionname + "\n", verbosity_level="error")
                Logger.log(exc + "\n", verbosity_level="error")
                Logger.log(sys.exc_info() + "\n", verbosity_level="error")
                Logger.log(str(traceback.extract_tb(sys.exc_info()[2])) + "\n", verbosity_level="error")

    resultlist.append(klee_result)
    Logger.log("done thread_flipper_phase_one on : " + functionname + " (flipped " + str(flip_counter) + " times)\n", verbosity_level="debug")

def thread_phase_one(
        resultlist, functionname, symmains_bc, outdir, timeout,
        flags, posixflags, posix4main, no_optimize=False, flipper_mode=False):
    """
    This function is executed by the parallel processes in phase one
    """
    Logger.log("thread_phase_one: " + functionname + "\n", verbosity_level="debug")

    # Just run KLEE on it
    try:
        resultlist.append(execute_klee(
            symmains_bc, functionname, outdir, timeout, flipper_mode, flags, posixflags, posix4main, no_optimize))
    # pylint: disable=broad-except
    except Exception as exc:
        Logger.log("A thread in phase one threw an exception\n", verbosity_level="error")
        Logger.log("The analyzed function was: " + functionname + "\n", verbosity_level="error")
        Logger.log(exc + "\n", verbosity_level="error")
        Logger.log(sys.exc_info() + "\n", verbosity_level="error")
        Logger.log(str(traceback.extract_tb(sys.exc_info()[2])) + "\n", verbosity_level="error")

    Logger.log("done thread_phase_one: " + functionname + "\n", verbosity_level="debug")


def thread_phase_two(
        resultlist, caller, callee, prepended_bc, outdir,
        flags, posixflags, posix4main, no_optimize=False):
    """
    This function is executed by the parallel processes in phase two
    """
    Logger.log("thread_phase_two\n", verbosity_level="debug")

    # And run klee on it
    try:
        resultlist.append(execute_klee_targeted_search(
            prepended_bc, caller, "__macke_error_" + callee, outdir,
            flags, posixflags, posix4main, no_optimize))
    # pylint: disable=broad-except
    except Exception as exc:
        print()
        print("A thread in phase two throws and exception")
        print("The analyzed caller/callee pair was:", caller, callee)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])
