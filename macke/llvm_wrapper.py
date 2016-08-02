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
