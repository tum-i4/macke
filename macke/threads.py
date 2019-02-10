"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager, FuzzResult
from .Logger import Logger
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
        resultlist.append(result)
        result.convert_erros_to_klee_files(["queue", "crashes"])
    except Exception as exc:
        print()
        print("A fuzz thread in phase one throws an exception")
        print("The analyzed function was:", functionname)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])
    cgroupqueue.put(cgroup)

    Logger.log("done thread_fuzz_phase_one: " + functionname + "\n", verbosity_level="debug")

# Arguments a combination of thread_fuzz_phase_one and thread_phase_one (symbolic) plus flippertime
# We parse the fuzztime in flags
def thread_flipper_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, afl_to_klee_dir, fuzztime,
                             symmains_bc, klee_outdir, flags, posixflags, posix4main, timeout, no_optimize=False,
                             flipper_mode=True
                             ):
    Logger.log("thread_flipper_phase_one: " + functionname + " (timeout " + str(timeout) + ")\n",
               verbosity_level="debug")

    progress_done = True
    klee_result = None
    fuzz_result = None

    flip_counter = 0

    timeout_timestamp = time.time() + timeout
    #afl_to_klee_dir = path.join(outdir, "afl_to_klee_dir") # macke_errors

    while progress_done and (time.time() < timeout_timestamp):
        # TODO: in case of no progress, keep going until at least some progress is done?
        progress_done = False

        if flip_counter > 0:
            Logger.log("Flipping!\n", verbosity_level="debug")
        flip_counter += 1

        # Run klee
        Logger.log("trying klee on: " + functionname + "\n", verbosity_level="debug")

        try:
            klee_result = execute_klee(
                symmains_bc, functionname, klee_outdir, flipper_mode, flags, posixflags, posix4main, no_optimize,
                afl_to_klee_dir)
        # pylint: disable=broad-except
        except Exception as exc:
            print()
            print("A thread in phase one threw an exception")
            print("The analyzed function was:", functionname)
            print(exc)
            print()
            print(sys.exc_info())
            traceback.print_tb(sys.exc_info()[2])

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
                except:
                    Logger.log("Unexpected error while processing klee output!\n", verbosity_level="error")
                    sys.exit(1)
                # argv = self.clean_argv(argv)
                #Logger.log("argv: " + str(argv) + "\n", verbosity_level="debug")
                time.sleep(2)

            else:
                Logger.log("KLEE has not made progress\n", verbosity_level="debug")


        # Run fuzzer
        Logger.log("trying afl on: " + functionname + "\n", verbosity_level="debug")

        cgroup = cgroupqueue.get()
        try:
            fuzz_result = fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, fuzztime, flipper_mode, afl_to_klee_dir)
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


    resultlist.append(klee_result)
    fuzz_result.convert_erros_to_klee_files(["queue", "crashes"])

    Logger.log("done thread_flipper_phase_one on : " + functionname + " (flipped " + str(flip_counter-1) + " times)\n", verbosity_level="debug")

def thread_phase_one(
        resultlist, functionname, symmains_bc, outdir,
        flags, posixflags, posix4main, no_optimize=False, flipper_mode=False):
    """
    This function is executed by the parallel processes in phase one
    """
    Logger.log("thread_phase_one: " + functionname + "\n", verbosity_level="debug")

    # Just run KLEE on it
    try:
        resultlist.append(execute_klee(
            symmains_bc, functionname, outdir, flipper_mode, flags, posixflags, posix4main, no_optimize))
    # pylint: disable=broad-except
    except Exception as exc:
        print()
        print("A thread in phase one threw an exception")
        print("The analyzed function was:", functionname)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])
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
