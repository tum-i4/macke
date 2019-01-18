"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager
from .Logger import Logger

import subprocess
import traceback
import sys

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

def test_phase():
    Logger.log("test_phase\n", verbosity_level="debug")


# Arguments a combination of thread_fuzz_phase_one and thread_phase_one (symbolic) plus flippertime
# We parse the fuzztime in flags
def thread_flipper_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, fuzztime,
                             symmains_bc, klee_outdir, flags, posixflags, posix4main, no_optimize=False,
                             flipper_mode=True
                             ):
    Logger.log("thread_flipper_phase_one: " + functionname + "\n", verbosity_level="debug")

    progress_done = True
    while progress_done:

        # Run fuzzer
        Logger.log("trying afl on: " + functionname + "\n", verbosity_level="debug")

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

        Logger.log("resultlist afl: " + str(resultlist) + "\n", verbosity_level="debug")
        # Translate fuzz files to klee files
        # TODO

        # Run klee
        Logger.log("trying klee on: " + functionname + "\n", verbosity_level="debug")

        try:
            resultlist.append(execute_klee(
                symmains_bc, functionname, klee_outdir, flipper_mode, flags, posixflags, posix4main, no_optimize))
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
        # TODO

        progress_done = False

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
