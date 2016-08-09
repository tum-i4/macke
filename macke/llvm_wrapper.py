"""
Functions, that wraps all llvm actions and transformation into python functions
"""
from .config import LLVMOPT, LIBMACKEOPT
import json
import subprocess


def __run_subprocess(popenargs):
    """
    Starts a subprocess with popenargs and returns it output
    """
    return subprocess.check_output(popenargs)


def __run_subprocess_with_json_output(popenargs):
    """
    Starts a subprocess with popenargs and returns the output as parsed json
    """
    out = __run_subprocess(popenargs)
    return json.loads(out.decode("utf-8"))


def list_all_funcs_topological(bitcodefile):
    """
    Wrapper around the list all functions pass. Any circles or strongly
    connected components are listed alphabetically in nested lists
    """
    return __run_subprocess_with_json_output([
        LLVMOPT, "-load", LIBMACKEOPT,
        "-listallfuncstopologic", bitcodefile,
        "-disable-output"])


def extract_callgraph(bitcodefile):
    """
    Wrapper around the extract callgraph pass
    """
    return __run_subprocess_with_json_output([
        LLVMOPT, "-load", LIBMACKEOPT,
        "-extractcallgraph", bitcodefile,
        "-disable-output"])


def encapsulate_symbolic(
        sourcefile, function, destfile=None, removeunused=True):
    """
    Wrapper around the encapsulate symbolic pass
    """
    # If no destfile is given, just modify the source file
    if destfile is None:
        destfile = sourcefile

    additional_passes = []
    if removeunused:
        # Add some passes to eliminate all unused functions
        additional_passes += [
            "-internalize-public-api-list=main",
            "-internalize", "-globalopt", "-globaldce", "-adce"]

    return __run_subprocess([
        LLVMOPT, "-load", LIBMACKEOPT,
        "-encapsulatesymbolic", sourcefile,
        "-encapsulatedfunction", function] + additional_passes +
        ["-o", destfile])


def prepend_error(sourcefile, function, errordirlist, destfile=None):
    """
    Wrapper around the prepend error pass
    """
    # If no destfile is given, just modify the source file
    if destfile is None:
        destfile = sourcefile

    errordirflags = []
    for errordir in errordirlist:
        errordirflags.append("-previouskleerundirectory")
        errordirflags.append(errordir)

    return __run_subprocess([
        LLVMOPT, "-load", LIBMACKEOPT, "-preprenderror", sourcefile,
        "-prependtofunction", function] + errordirflags + ["-o", destfile])
