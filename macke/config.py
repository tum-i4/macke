"""
Load global configurations, if they exist in a config.ini file
"""

import configparser
from os import path
import subprocess

CONFIG = configparser.ConfigParser()
CONFIGFILE = path.join(path.dirname(__file__), "..", "config.ini")
CONFIG.read(CONFIGFILE)

LIBMACKEOPT = CONFIG.get("binaries", "libmackeopt")
LLVMOPT = CONFIG.get("binaries", "llvmopt", fallback="opt")
KLEEBIN = CONFIG.get("binaries", "klee", fallback="klee")
THREADNUM = CONFIG.getint("runtime", "threadnum", fallback=None)


def __get_output_from(*args, **kwargs):
    # Sadly, some programs return their help pages with non-zero exit code
    try:
        output = subprocess.check_output(*args, **kwargs)
    except subprocess.CalledProcessError as ex:
        output = ex.output
    return output


def check_config():
    # Check, if LLVMOPT is actually a binary of opt
    if (not path.isfile(LLVMOPT) or b"llvm .bc -> .bc modular optimizer"
            not in __get_output_from([LLVMOPT, "-help"])):
        raise Exception("Config: Invalid opt binary")

    # Check, if LLVMOPT is the correct opt version
    if b"LLVM version 3.4.2" not in __get_output_from([LLVMOPT, "-version"]):
        raise Exception("Config: Invalid opt version")

    # Check, if LIBMACKEOPT actually supports the relevant passes
    if not path.isfile(LIBMACKEOPT):
        raise Exception("Config: Invalid libmackeopt binary")
    mhelp = __get_output_from([LLVMOPT, "-load", LIBMACKEOPT, "-help"])
    if any(t not in mhelp for t in [
            b"-extractcallgraph", b"-listallfuncstopologic",
            b"-encapsulatesymbolic", b"-preprenderror"]):
        raise Exception(
            "Config: limackeopt does not support all required passes")

    # Check, if KLEEBIN
    if not path.isfile(KLEEBIN):
        raise Exception("Config: Invalid KLEE binary")
    kvers = __get_output_from([KLEEBIN, "-version"])
    if b"KLEE" not in kvers or b"LLVM version 3.4.2" not in kvers:
        raise Exception("Config: Invalid klee version")
    khelp = __get_output_from([KLEEBIN, "-help"])
    if any(t not in khelp for t in [b"=ld2t", b"-targeted-function=<string>"]):
        raise Exception("Config: klee does not support targeted search")

    # Check, if a reasonable number of threads is used
    if THREADNUM is not None and not 0 < THREADNUM < 128:
        raise Exception("Config: Invalid Number of threads")
