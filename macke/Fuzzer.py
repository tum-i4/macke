
"""
All interactions with fuzzing
"""

import subprocess
import time
import signal

from os import environ, path, makedirs, listdir, kill

from .config import LIBMACKEOPT, LIBMACKEFUZZPATH, LIBMACKEFUZZOPT, LLVMOPT, LLVMFUZZOPT, CLANG, AFLBIN, AFLLIB, AFLCC, AFLFUZZ, AFLTMIN

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
    output = b""
    err = b""
    while p.poll() is None:
        (o, e) = p.communicate(None)
        output += o
        err += e

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
        crashcorpus = path.join(outdir, "crashes")

        self.find_errors(inputcorpus, crashcorpus)


    def find_errors(self, inputcorpus, crashcorpus):
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

        inputdirectories = [inputcorpus, crashcorpus]

        if any(not path.exists(d) for d in inputdirectories):
            self.fuzzmanager.print_func("Couldn't fuzz: " + self.analyzedfunc)
            return

        for d in inputdirectories:
            for f in listdir(d):
                if not f.startswith("id:"):
                    continue
                fname = path.join(d, f)
                if not path.isfile(fname):
                    continue
                self.testcount += 1
                reproduced = self.fuzzmanager.execute_reproducer(fname, self.analyzedfunc)
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
    def __init__(self, bcfile, fuzzdir, builddir, cflags = None, stop_when_done=False, smart_input=True, input_maxlen=32, print_func=print):
        """
        Compile necessary binaries and save the names to them
        """
        self.cflags = [] if cflags is None else cflags
        self.fuzzdir = fuzzdir
        self.inputbasedir = path.join(fuzzdir, "input")
        self.inputforfunc = dict()
        self.builddir = builddir
        self.orig_bcfile = bcfile
        self.smart_input = smart_input
        self.print_func = print_func
        self.input_maxlen = input_maxlen
        makedirs(self.inputbasedir)

        ## Set necessary environment
        environ["AFL_PATH"] = AFLLIB
        environ["AFL_CC"] = CLANG
        environ["AFL_NO_UI"] = "1"
        environ["AFL_QUIET"] = "1"
        environ["AFL_SKIP_CRASHES"] = "1"
        if(stop_when_done):
            environ["AFL_EXIT_WHEN_DONE"] = "1"

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
        self.print_func("Compiling helper functions for fuzzer...")
        _run_checked_silent_subprocess([AFLCC, "-c", "-g"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_afl_instrumented])
        _run_checked_silent_subprocess([AFLCC, "-c", "-g"] + self.cflags + [initializer_source_path, "-o", initializer_afl_instrumented])
        # For reproducer
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_reproducer])
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address", "-D__REPRODUCE_FUZZING"] + self.cflags + [initializer_source_path, "-o", initializer_reproducer])

        ## Instrument the bcfile
        # Add drivers
        self.print_func("Instrument bc file with fuzzer drivers...")
        _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-insert-fuzzdriver",
            "-renamemain", "-mem2reg", bcfile, "-o", target_with_drivers])
        # Add with asan for reproducer
        self.print_func("Adding asan for reproducer...")
        _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-enable-asan",
            target_with_drivers, "-o", target_with_drivers_and_asan])



        # link general driver
        self.print_func("linking fuzz-target...")
        self.afltarget = path.join(builddir, "afl-target")
        _run_checked_silent_subprocess([AFLCC] + self.cflags + ["-o", self.afltarget, buffer_extract_afl_instrumented, initializer_afl_instrumented, target_with_drivers])

        # link reproducer
        self.print_func("linking reproducer...")
        self.reproducer = path.join(builddir, "reproducer")
        _run_checked_silent_subprocess([CLANG, "-v", "-fsanitize=address"] + self.cflags + ["-o", self.reproducer, buffer_extract_reproducer, initializer_reproducer, target_with_drivers_and_asan])

        self.init_inputdirs()



    def init_inputdirs(self):
        functions = self.list_suitable_drivers()

        if self.smart_input:
            for f in functions:
                inputdir = path.join(self.inputbasedir, f)
                makedirs(inputdir)
                self.inputforfunc[f] = inputdir
                self.execute_inputgenerator(f, inputdir)
        else:
            self.init_empty_inputdir()
            for f in functions:
                self.inputforfunc[f] = self.inputbasedir

    def init_empty_inputdir(self):
        if _dir_contains_no_files(self.inputbasedir):
            dummy_file = path.join(self.inputbasedir, "dummy.input")
            f = open(dummy_file, "w")
            f.write("a")
            f.close()

    def list_suitable_drivers(self):
        """ Call the target to list all drivers, strip newline at end and split at newlines """
        return subprocess.check_output([self.afltarget, "--list-fuzz-drivers"]).decode("utf-8").strip().split('\n')


    def execute_inputgenerator(self, func, targetdir):
        subprocess.check_output([self.afltarget, "--generate-for=" + func, targetdir, str(self.input_maxlen)])

    def execute_reproducer(self, inputfile, functionname):
        infd = open(inputfile, "r")
        (returncode, stdoutdata, stderrdata) = _run_subprocess(
            [self.reproducer, "--fuzz-driver=" + functionname], stdin=infd)
        ret = AsanResult(stderrdata, inputfile, functionname)
        infd.close()
        return ret

    def execute_afl_fuzz(self, functionname, outdir, fuzztime):
        errordir = path.join(outdir, "macke_errors")
        # This creates outdir + error dir
        makedirs(errordir)

        outfd = open(path.join(outdir, "output.txt"), "w")
        proc = subprocess.Popen([AFLFUZZ, "-i", self.inputforfunc[functionname], "-o", outdir, self.afltarget, "--fuzz-driver=" + functionname], stdout=outfd, stderr=outfd)

        time.sleep(fuzztime)
        try:
            kill(proc.pid, signal.SIGINT)
            # wait for afl-fuzz to cleanup
            proc.wait();
        except OSError:
            pass
        outfd.close()

        # afl-fuzz sometimes does not cleanup the target correctly, do it here
        try:
            pidstr = subprocess.check_output(["pgrep", "-x", "-f", self.afltarget + " --fuzz-driver=" + functionname]).decode("ascii")
            pids = pidstr.split('\n')
            kill(int(pids[0]), signal.SIGKILL)
        except subprocess.CalledProcessError as ex:
            pass

        return FuzzResult(self, functionname, errordir, outdir);


    def execute_afl_tmin(self, inputfile, outputfile, functionname):
        _run_checked_silent_subprocess([AFLTMIN, "-t", "50", "-i", inputfile, "-o", outputfile, "--", self.afltarget, "--fuzz-driver=" + functionname])
        return

    def minimize_crash(self, crashinputfile, asanerror, function):
        minimized_name = path.join(path.dirname(crashinputfile), "min_" + path.basename(crashinputfile))
        # tmin fails on timeout - catch this case
        try:
            self.execute_afl_tmin(crashinputfile, minimized_name, function)
            asanresult = self.execute_reproducer(minimized_name, function)
            if asanresult.iserror and asanresult.stack == asanerror.stack:
                return asanresult
        except subprocess.CalledProcessError:
            pass
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
