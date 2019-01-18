"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager
from .Logger import Logger
from .read_klee_testcases import process_klee_out

import subprocess
import traceback
import sys
import glob
import time

# We parse the fuzztime in flags
def thread_fuzz_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, fuzztime, flipper_mode):
    Logger.log("thread_fuzz_phase_one: " + functionname + "\n", verbosity_level="debug")
    cgroup = cgroupqueue.get()
    try:
        resultlist.append(fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, fuzztime, flipper_mode))
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
def thread_flipper_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, fuzztime,
                             symmains_bc, klee_outdir, flags, posixflags, posix4main, no_optimize=False,
                             flipper_mode=True
                             ):
    Logger.log("thread_flipper_phase_one: " + functionname + "\n", verbosity_level="debug")

    progress_done = True
    resultlist_size = len(resultlist)
    while progress_done: # TODO: add timeout check here
        progress_done = False

        # Run klee
        Logger.log("trying klee on: " + functionname + "\n", verbosity_level="debug")

        try:
            result = execute_klee(
                symmains_bc, functionname, klee_outdir, flipper_mode, flags, posixflags, posix4main, no_optimize)
            resultlist.append(result)
        # pylint: disable=broad-except
        except Exception as exc:
            print()
            print("A thread in phase one threw an exception")
            print("The analyzed function was:", functionname)
            print(exc)
            print()
            print(sys.exc_info())
            traceback.print_tb(sys.exc_info()[2])

        Logger.log("resultlist klee: " + str(resultlist) + "\n", verbosity_level="debug")

        # Translate klee files to fuzz files

        if result:
            if result.progress:
                progress_done = True
                Logger.log("KLEE has made progress (" + str(result.progress) + ")\n", verbosity_level="info")
                argv = []
                Logger.log("klee_outdir: " + klee_outdir + "\n", verbosity_level="debug")
                #for k in glob.glob(klee_outdir + "/klee-*"):
                #    argv.extend(process_klee_out(k, fuzzmanager.inputbasedir + "/input"))
                argv.extend(process_klee_out(klee_outdir, fuzzmanager.inputbasedir))

                # argv = self.clean_argv(argv)
                Logger.log("argv: " + str(argv) + "\n", verbosity_level="debug")
                time.sleep(2)

            else:
                Logger.log("KLEE has not made progress\n", verbosity_level="debug")

        # Run fuzzer
        Logger.log("trying afl on: " + functionname + "\n", verbosity_level="debug")

        cgroup = cgroupqueue.get()
        try:
            result = fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, fuzztime, flipper_mode)
            resultlist.append(result)
        except Exception as exc:
            print()
            print("A fuzz thread in phase one throws an exception")
            print("The analyzed function was:", functionname)
            print(exc)
            print()
            print(sys.exc_info())
            traceback.print_tb(sys.exc_info()[2])
        cgroupqueue.put(cgroup)

        if result:
            if result.progress:
                progress_done = True
                Logger.log("AFL has made progress (" + str(result.progress) + ")\n", verbosity_level="info")
            else:
                Logger.log("AFL has not made progress\n", verbosity_level="debug")

        Logger.log("resultlist afl: " + str(resultlist) + "\n", verbosity_level="debug")

        # fuzz files are already translated to klee files

    Logger.log("done thread_flipper_phase_one: " + functionname + "\n", verbosity_level="debug")

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
