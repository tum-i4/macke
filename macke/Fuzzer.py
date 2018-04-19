
"""
All interactions with fuzzing
"""

import subprocess
import time
import signal

from os import environ, path, makedirs, listdir, kill

from .config import LIBMACKEOPT, LIBMACKEFUZZPATH, LIBMACKEFUZZOPT, LLVMOPT, LLVMFUZZOPT, CLANG, AFLBIN, AFLLIB, AFLCC, AFLFUZZ

from .Asan import AsanResult
from .Error import Error


def _dir_contains_no_files(dirname):
    return not any(path.isfile(f) for f in listdir(dirname))

def _run_checked_silent_subprocess(popenargs):
    subprocess.check_output(popenargs, stderr=subprocess.STDOUT)

def _run_subprocess(*args, **kwargs):
    """
    Starts a subprocess, waits for it and returns (exitcode, output, erroutput)
    """
    p = subprocess.Popen(*args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = ""
    err = ""
    while p.poll() is None:
        (o, e) = p.communicate(None)
        output += o.decode("utf-8")
        err += e.decode("utf-8")

    return p.returncode, output, err


class FuzzResult:
    """
    Container, that stores all information about a afl fuzzing run
    """
    def __init__(self, fuzzmanager, functionname, errordir, outdir):
        self.fuzzmanager = fuzzmanager

        # duck typing - behave similar to kleeresult
        self.analyzedfunc = functionname
        self.outdir = errordir
        self.fuzzoutdir = outdir

        inputcorpus = path.join(outdir, "queue")
        self.find_errors(fuzzmanager.reproducer, inputcorpus)


    def find_errors(self, reproducer, inputcorpus):
        """
        Calls reproducer on all inputs and calculates statistics
        """
        #print("calling reproducer on found paths for function " + self.analyzedfunc)
        self.errorlist = []
        asanerrorlist = []

        # again duck typing names
        self.errfiles = []
        self.testcount = 0
        self.errorcount = 0

        for f in listdir(inputcorpus):
            fname = path.join(inputcorpus, f)
            if not path.isfile(fname):
                continue
            self.testcount += 1
            infd = open(fname, "r")
            (returncode, stdoutdata, stderrdata) = _run_subprocess(
                [reproducer, "--fuzz-driver=" + self.analyzedfunc], stdin=infd)
            reproduced = AsanResult(stderrdata, fname, self.analyzedfunc)
            infd.close()
            if reproduced.iserror:
                error = self.fuzzmanager.minimize_crash(fname, reproduced, self.analyzedfunc)
                self.errorcount += 1
                self.errfiles.append(fname)
                asanerrorlist.append(error)

        # Convert AsanErrors to ktests (and ktest.errs)
        for i in range(0, len(asanerrorlist)):
            errname = "fuzzer%0.5d" % i
            errfile = asanerrorlist[i].convert_to_ktest(self.fuzzmanager, self.outdir, errname)
            self.errorlist.append(Error(errfile, self.analyzedfunc))


    def get_outname(self):
        """ Get the directory name of the fuzzer output directory """
        return path.basename(self.fuzzoutdir)

    def get_errors(self):
        return self.errorlist



class FuzzManager:
    """
    Manages relevant global resources for fuzzing and
    """
    def __init__(self, bcfile, fuzzdir, builddir, cflags = None):
        """
        Compile necessary binaries and save the names to them
        """
        self.cflags = [] if cflags is None else cflags
        self.fuzzdir = fuzzdir
        self.inputdir = path.join(fuzzdir, "inputdir")
        self.builddir = builddir
        self.orig_bcfile = bcfile
        makedirs(self.inputdir)

        ## Set necessary environment
        environ["AFL_PATH"] = AFLLIB
        environ["AFL_CC"] = CLANG
        environ["AFL_NO_UI"] = "1"
        environ["AFL_QUIET"] = "1"

        ## Save paths temporarily for future compiling
        buffer_extract_source_path = path.join(LIBMACKEFUZZPATH, "helper_funcs", "buffer_extract.c")
        initializer_source_path = path.join(LIBMACKEFUZZPATH, "helper_funcs", "initializer.c")
        buffer_extract_afl_instrumented = path.join(builddir, "buffer_extract_afl.o")
        initializer_afl_instrumented = path.join(builddir, "initializer_afl.o")
        buffer_extract_reproducer = path.join(builddir, "buffer_extract_reproducer.o")
        initializer_reproducer = path.join(builddir, "initializer_reproducer.o")
        target_with_drivers = path.join(builddir, "target_with_drivers.bc")
        target_with_drivers_and_asan = path.join(builddir, "target_with_drivers_and_asan.bc")

        ## Compile helper functions
        # For afl
        _run_checked_silent_subprocess([AFLCC, "-c", "-g"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_afl_instrumented])
        _run_checked_silent_subprocess([AFLCC, "-c", "-g"] + self.cflags + [initializer_source_path, "-o", initializer_afl_instrumented])
        # For reproducer
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_reproducer])
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address", "-D__REPRODUCE_FUZZING"] + self.cflags + [initializer_source_path, "-o", initializer_reproducer])

        ## Instrument the bcfile
        # Add drivers
        _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-insert-fuzzdriver",
            "-renamemain", "-mem2reg", bcfile, "-o", target_with_drivers])
        # Add with asan for reproducer
        _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-enable-asan",
            "-asan", "-asan-module", target_with_drivers, "-o", target_with_drivers_and_asan])


        # Compile general driver
        self.afltarget = path.join(builddir, "afl-target")
        _run_checked_silent_subprocess([AFLCC] + self.cflags + ["-o", self.afltarget, buffer_extract_afl_instrumented, initializer_afl_instrumented, target_with_drivers])

        # Compile reproducer
        self.reproducer = path.join(builddir, "reproducer")
        _run_checked_silent_subprocess([AFLCC, "-fsanitize=address"] + self.cflags + ["-o", self.reproducer, buffer_extract_reproducer, initializer_reproducer, target_with_drivers_and_asan])



    def init_empty_inputdir(self):
        if _dir_contains_no_files(self.inputdir):
            dummy_file = path.join(self.inputdir, "dummy.input")
            f = open(dummy_file, "w")
            f.write("a")
            f.close()

    def list_suitable_drivers(self):
        """ Call the target to list all drivers, strip newline at end and split at newlines """
        return subprocess.check_output([self.afltarget, "--list-fuzz-drivers"]).decode("utf-8").strip().split('\n')

    def execute_reproducer(self, functionname):
        return subprocess.check_output([self.reproducer, "--fuzz-driver=" + functionname])

    def execute_afl_fuzz(self, functionname, outdir, fuzztime):
        outfd = open("/dev/null", "w")
        proc = subprocess.Popen([AFLFUZZ, "-i", self.inputdir, "-o", outdir, self.afltarget, "--fuzz-driver=" + functionname], stdout=outfd, stderr=outfd)

        time.sleep(fuzztime)
        kill(proc.pid, signal.SIGTERM)
        outfd.close()

        errordir = path.join(outdir, "macke_errors")
        makedirs(errordir)

        return FuzzResult(self, functionname, errordir, outdir);

    def minimize_crash(self, crashinputfile, asanerror, function):
        # Stub at the moment
        return asanerror


    def run_ktest_converter(self, function, inputfile, outfile, kleeargs):
        """
        Creates a ktest from an inputfile
        """
        if not kleeargs:
            kleeargs.append("<fuzzed function '" + function + "'>")
        kleeargflags = []
        for kleearg in kleeargs:
            kleeargflags.append("-kleeargs")
            kleeargflags.append(kleearg)


        _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-generate-ktest", "-ktestfunction=" + function,
            "-ktestinputfile=" + inputfile] + kleeargflags + ["-ktestout=" + outfile, "-disable-output", self.orig_bcfile]);
