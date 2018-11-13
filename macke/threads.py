"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager


import subprocess
import traceback
import sys

#TODO: define thread_flipper_phase_one here
#TODO: arguments a combination of thread_fuzz_phase_one and thread_phase_one (symbolic) plus flippertime
def thread_flipper_phase_one():
    pass

# We parse the fuzztime in flags
def thread_fuzz_phase_one(fuzzmanager, cgroupqueue, resultlist, functionname, outdir, fuzztime):
    cgroup = cgroupqueue.get()
    try:
        #TODO: copy this call into thread_flipper_phase_one and add saturation check
        resultlist.append(fuzzmanager.execute_afl_fuzz(cgroup, functionname, outdir, fuzztime))
    except Exception as exc:
        print()
        print("A fuzz thread in phase one throws an exception")
        print("The analyzed function was:", functionname)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])
    cgroupqueue.put(cgroup)


def thread_phase_one(
        resultlist, functionname, symmains_bc, outdir,
        flags, posixflags, posix4main):
    """
    This function is executed by the parallel processes in phase one
    """
    # Just run KLEE on it
    try:
        resultlist.append(execute_klee(
            symmains_bc, functionname, outdir, flags, posixflags, posix4main))
    # pylint: disable=broad-except
    except Exception as exc:
        print()
        print("A thread in phase one throws and exception")
        print("The analyzed function was:", functionname)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])


def thread_phase_two(
        resultlist, caller, callee, prepended_bc, outdir,
        flags, posixflags, posix4main):
    """
    This function is executed by the parallel processes in phase two
    """
    # And run klee on it
    try:
        resultlist.append(execute_klee_targeted_search(
            prepended_bc, caller, "__macke_error_" + callee, outdir,
            flags, posixflags, posix4main))
    # pylint: disable=broad-except
    except Exception as exc:
        print()
        print("A thread in phase two throws and exception")
        print("The analyzed caller/callee pair was:", caller, callee)
        print(exc)
        print()
        print(sys.exc_info())
        traceback.print_tb(sys.exc_info()[2])
