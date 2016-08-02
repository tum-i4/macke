"""
Functions, that wraps all llvm actions and transformation into python functions
"""
from .config import LLVMOPT, LIBMACKEOPT
import json
import subprocess


def extract_callgraph(bitcodefile):

    jsonout = subprocess.check_output([
        LLVMOPT, "-load", LIBMACKEOPT,
        "-extractcallgraph", bitcodefile,
        "-disable-output"])

    return json.loads(jsonout.decode("utf-8"))


def encapsulate_symbolic(sourcefile, function, outfile=None):

    # If no outfile is given, just modify the source file
    if outfile is None:
        outfile = sourcefile

    out = subprocess.check_output([
        LLVMOPT, "-load", LIBMACKEOPT,
        "-encapsulatesymbolic", sourcefile,
        "-encapsulatedfunction", function,
        "-o", outfile])

    return out
