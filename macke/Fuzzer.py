
"""
All interactions with fuzzing
"""

import subprocess
import time
import signal

from os import environ, path, makedirs, listdir, kill

from .config import LIBMACKEOPT, LIBMACKEFUZZPATH, LIBMACKEFUZZOPT, LLVMOPT, LLVMFUZZOPT, CLANG, AFLBIN, AFLLIB, AFLCC, AFLFUZZ


def _dir_contains_no_files(dirname):
    return not any(path.isfile(f) for f in listdir(dirname))


class FuzzResult:
    """
    Container, that stores all information about a afl fuzzing run
    """
    def __init__(self, reproducer, functionname, errordir, outdir):
        self.functionname = functionname
        self.outdir = outdir
        self.errordir = errordir

        inputcorpus = path.join(outdir, "queue")
        find_errors(reproducer, inputcorpus)


    def find_errors(self, reproducer, inputcorpus):
        print("calling reproducer on found paths for function" + functionname)
        self.errorlist = []
        for f in listdir(inputcorpus):
            if not path.isfile(inputcorpus):
                continue
            infd = open(f, "r")
            reproduced = AsanResult(subprocess.check_output([
                reproducer, "--fuzz-driver=" + self.functionname], stdin=infd))
            infd.close()
            if reproduced.iserror:
                errorlist.append(reproduced)


    def get_outname(self):
        """ Get the directory name of the fuzzer output directory """
        return path.basename(self.outdir)

    def get_errors(self):
        return None



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
        makedirs(self.inputdir)

        print("made inputdir " + self.inputdir)

        ## Set necessary environment
        environ["AFL_PATH"] = AFLLIB
        environ["AFL_CC"] = CLANG
        environ["AFL_NO_UI"] = "1"

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
        subprocess.check_call([AFLCC, "-c", "-g"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_afl_instrumented])
        subprocess.check_call([AFLCC, "-c", "-g"] + self.cflags + [initializer_source_path, "-o", initializer_afl_instrumented])
        # For reproducer
        subprocess.check_call([CLANG, "-c", "-g", "-fsanitize=address"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_reproducer])
        subprocess.check_call([CLANG, "-c", "-g", "-fsanitize=address", "-D__REPRODUCE_FUZZING"] + self.cflags + [initializer_source_path, "-o", initializer_reproducer])

        ## Instrument the bcfile
        # Add drivers
        subprocess.check_call([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-insert-fuzzdriver",
            "-renamemain", "-mem2reg", bcfile, "-o", target_with_drivers])
        # Add with asan for reproducer
        subprocess.check_call([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-enable-asan",
            "-asan", "-asan-module", target_with_drivers, "-o", target_with_drivers_and_asan])


        # Compile general driver
        self.afltarget = path.join(builddir, "afl-target")
        subprocess.check_call([AFLCC] + self.cflags + ["-o", self.afltarget, buffer_extract_afl_instrumented, initializer_afl_instrumented, target_with_drivers])

        # Compile reproducer
        self.reproducer = path.join(builddir, "reproducer")
        subprocess.check_call([AFLCC, "-fsanitize=address"] + self.cflags + ["-o", self.reproducer, buffer_extract_reproducer, initializer_reproducer, target_with_drivers_and_asan])




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
        kill(proc.pid, signal.SIGKILL)
        outfd.close()

        print("now getting fuzzresults...")

        return FuzzResult(reproducer, functionname, errordir, outdir);

