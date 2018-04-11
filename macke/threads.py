"""
All functions, that are executed in parallel threads
"""

from .Klee import execute_klee, execute_klee_targeted_search

from .Fuzzer import FuzzManager


# We parse the fuzztime in flags
def thread_fuzz_phase_one(fuzzmanager, resultlist, functionname, outdir, flags):
    fuzztime = 60
    print("starting thread")
    resultlist.append(fuzzmanager.execute_afl_fuzz(functionname, outdir, fuzztime))
    print("ended thread")


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


def thread_phase_two(
        resultlist, caller, callee, prepended_bc, outdir,
        flags, posixflags, posix4main):
    """
    This function is executed by the parallel processes in phase two
    """
    # And run klee on it
    try:
        resultlist.append(execute_klee_targeted_search(
            prepended_bc, caller, callee, outdir,
            flags, posixflags, posix4main))
    # pylint: disable=broad-except
    except Exception as exc:
        print()
        print("A thread in phase two throws and exception")
        print("The analyzed caller/callee pair was:", caller, callee)
        print(exc)
        print()
