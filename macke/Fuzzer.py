
"""
All interactions with fuzzing
"""

import subprocess
import time
import signal
import shutil

from os import environ, path, makedirs, listdir, kill, killpg, getpgid, setsid
from multiprocessing import Manager, Pool
import os, sys
import stat
import tempfile

from .config import LIBMACKEOPT, LIBMACKEFUZZPATH, LIBMACKEFUZZOPT, LLVMOPT, LLVMFUZZOPT, CLANG, AFLBIN, AFLLIB, AFLCC, AFLFUZZ, AFLTMIN, THREADNUM
from .constants import FUZZFUNCDIR_PREFIX

from .Asan import AsanResult
from .Error import Error
from .callgrind import get_coverage

from .cgroups import cgroups_run_timed_subprocess, cgroups_run_checked_silent_subprocess, cgroups_Popen

from .Logger import Logger

def _dir_contains_no_files(dirname):
    return not any(path.isfile(f) for f in listdir(dirname))

def _run_checked_silent_subprocess(command, **kwargs):
    try:
        p = subprocess.check_output(command, stderr=subprocess.STDOUT, **kwargs)
        return p
    except subprocess.CalledProcessError as pexc:
        print("Error code %d: %s"%(pexc.returncode, pexc.output.decode('utf-8')))
        sys.exit(pexc.returncode)

def _run_subprocess(*args, **kwargs):
    """
    Starts a subprocess, waits for it and returns (exitcode, output, erroutput)
    """
    p = subprocess.Popen(*args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=setsid)
    output = b""
    err = b""
    try:
        while p.poll() is None:
            (o, e) = p.communicate(None, timeout=1)
            output += o
            err += e
    # On hangup kill the program (and children)
    except subprocess.TimeoutExpired:
        killpg(getpgid(p.pid), signal.SIGKILL)

    return p.returncode, output, err


def extract_fuzzer_coverage(macke_directory):
    # Get absolute path since we are going to switch directories
    macke_directory = path.abspath(macke_directory)
    fuzzer_dir = path.join(macke_directory, "fuzzer")

    if not path.exists(fuzzer_dir):
        return dict()

    # Look for afltarget
    builddir = path.join(fuzzer_dir, "build")
    if not path.exists(builddir):
        return dict()

    afltarget = path.join(builddir, "afl-target")
    if not path.exists(afltarget) or not path.isfile(afltarget):
        return dict()

    # switch cwd for going through inputs
    tmpdir = tempfile.mkdtemp(prefix="macke_tmp_callgrind_")

    old_cwd = os.getcwd()
    os.chdir(tmpdir)

    environ["LIBC_FATAL_STDERR_"] = "1"
    # gather coverage results in parallel
    pool = Pool(THREADNUM)
    manager = Manager()
    queue = manager.Queue()

    async_results = []

    for fundir in listdir(fuzzer_dir):
        if not fundir.startswith(FUZZFUNCDIR_PREFIX):
            continue
        analyzedfunc = fundir[len(FUZZFUNCDIR_PREFIX):]
        fdpath = path.join(fuzzer_dir, fundir)
        inputdirectories = [ path.join(fdpath, "queue"), path.join(fdpath, "crashes"), path.join(fdpath, "hangs") ]

        # If a function could not be fuzzed
        if any(not path.exists(d) for d in inputdirectories):
            continue

        args = [afltarget, "--fuzz-driver=" + analyzedfunc]

        for d in inputdirectories:
            for f in listdir(d):
                # Only look at afl inputs
                if not f.startswith("id:"):
                    continue
                inputfilename = path.join(d, f)
                # When we miss permissions for file, add permissions
                if not os.access(inputfilename, os.R_OK):
                    os.chmod(inputfilename, stat.S_IRUSR)
                if not path.isfile(inputfilename):
                    continue

                async_results.append(pool.apply_async(get_coverage, (args, inputfilename), callback=queue.put))
    # After registering all jobs, close the pool
    pool.close()

    def process_queue():
        while not queue.empty():
            for file, info in queue.get().items():
                if file in coverage:
                    coverage[file]['covered'] |= info['covered']
                else:
                    coverage[file] = info


    coverage = dict()
    while async_results:
        async_results = list(filter(lambda a : not a.ready(), async_results))
        process_queue()
        time.sleep(0.2)
    pool.join()
    process_queue()
    os.chdir(old_cwd)
    shutil.rmtree(tmpdir)

    return coverage




class FuzzResult:
    """
    Container, that stores all information about a afl fuzzing run
    """
    def __init__(self, fuzzmanager, cgroup, functionname, errordir, outdir):
        self.fuzzmanager = fuzzmanager
        self.cgroup = cgroup

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

                # When we miss permissions for file, add permissions
                if not os.access(fname, os.R_OK):
                    os.chmod(fname, stat.S_IRUSR)

                if not path.isfile(fname):
                    continue
                self.testcount += 1
                reproduced = self.fuzzmanager.execute_reproducer(self.cgroup, fname, self.analyzedfunc)
                if reproduced.iserror and reproduced.has_stack_trace():
                    error = self.fuzzmanager.minimize_crash(self.cgroup, fname, reproduced, self.analyzedfunc)
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
    def __init__(self, bcfile, fuzzdir, builddir, lflags = None, cflags = None, stop_when_done=False, smart_input=True, input_maxlen=32, print_func=print, flipper_mode=False):
        """
        Compile necessary binaries and save the names to them
        """
        self.cflags = [] if cflags is None else cflags
        self.lflags = [] if lflags is None else lflags
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
        environ["AFL_TMIN_EXACT"] = "1"
        if(stop_when_done):
            environ["AFL_EXIT_WHEN_DONE"] = "1"
        # Print fatal errors on stderr instead of tty
        environ["LIBC_FATAL_STDERR_"] = "1"

        asan_env = environ.copy()
        asan_env["AFL_USE_ASAN"] = "1"

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
        _run_checked_silent_subprocess([CLANG, "-c", "-g"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_afl_instrumented])
        _run_checked_silent_subprocess([AFLCC, "-c", "-g"] + self.cflags + [initializer_source_path, "-o", initializer_afl_instrumented])
        # For reproducer
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address"] + self.cflags + [buffer_extract_source_path, "-o", buffer_extract_reproducer])
        _run_checked_silent_subprocess([CLANG, "-c", "-g", "-fsanitize=address", "-D__REPRODUCE_FUZZING"] + self.cflags + [initializer_source_path, "-o", initializer_reproducer])

        ## Instrument the bcfile
        # Add drivers
        self.print_func("Instrument bc file with fuzzer drivers...")
        Logger.log(LLVMFUZZOPT + " -load " + LIBMACKEFUZZOPT + " -insert-fuzzdriver" +
            " -renamemain" + " -mem2reg " + bcfile + " -o " + target_with_drivers)
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
        _run_checked_silent_subprocess([AFLCC, "-O3"] + self.lflags + ["-o", self.afltarget, buffer_extract_afl_instrumented, initializer_afl_instrumented, target_with_drivers])

        # link reproducer
        self.print_func("linking reproducer...")
        self.reproducer = path.join(builddir, "reproducer")
        _run_checked_silent_subprocess([CLANG, "-v", "-fsanitize=address"] + self.lflags + ["-o", self.reproducer, buffer_extract_reproducer, initializer_reproducer, target_with_drivers_and_asan])

        # link minimizer
        self.print_func("linking minimizer...")
        self.minimizer = path.join(builddir, "afl_minimizer")
        _run_checked_silent_subprocess([AFLCC, "-O3"] + self.lflags + ["-o", self.minimizer, buffer_extract_afl_instrumented, initializer_afl_instrumented, target_with_drivers], env=asan_env)

        self.init_inputdirs()

        self.flipper_mode = flipper_mode

        # saturation computation
        self.already_processed_lines = 1
        self.saturation_index = 0


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
            dummy_file2 = path.join(self.inputbasedir, "dummy_a.input")
            f = open(dummy_file, "wb")
            f.write(b'\0')
            f.close()
            f = open(dummy_file2, "wb")
            f.write(b'a')
            f.close()

    def list_suitable_drivers(self):
        """ Call the target to list all drivers, strip newline at end and split at newlines """
        return subprocess.check_output([self.afltarget, "--list-fuzz-drivers"]).decode("utf-8").strip().split()


    def execute_inputgenerator(self, func, targetdir):
        subprocess.check_output([self.afltarget, "--generate-for=" + func, targetdir, str(self.input_maxlen)])

    def execute_reproducer(self, cgroup, inputfile, functionname):
        menv = environ.copy()
        menv["ASAN_OPTIONS"] = "detect_leaks=0"
        infd = open(inputfile, "r")
        (returncode, stdoutdata, stderrdata) = cgroups_run_timed_subprocess(
            [self.reproducer, "--fuzz-driver=" + functionname], cgroup=cgroup, stdin=infd, env=menv)
        ret = AsanResult(stderrdata, inputfile, functionname)
        infd.close()
        return ret

    # Function to check for saturation of AFL
    def afl_saturated(self, outdir: str):
        if not os.path.exists(os.path.join(os.path.join(outdir, "plot_data"))):
            Logger.log("afl_saturated - " + outdir + "/plot_data does not exist (yet)\n", verbosity_level="debug")
            return False

        # saturated means:
        # 3x timestamps with no pending totals and no pending favs
        # detected cycles count as 2x such timestamps

        saturated = False

        with open(os.path.join(os.path.join(outdir, "plot_data")), "r") as plot_data:
            lines = plot_data.readlines()

            if len(lines) <= 1:
                # the first line is always the header
                # nothing to analyze yet
                return False

            number_of_interesting_lines = len(lines) - self.already_processed_lines
            Logger.log("interesting lines " + str(number_of_interesting_lines) + "/" + str(len(lines)) + "\n", verbosity_level="debug")
            self.already_processed_lines = number_of_interesting_lines

            # one line is of form:
            # unix_time, cycles_done, cur_path, paths_total,
            # pending_total, pending_favs, map_size (float %),
            # unique_crashes, unique_hangs, max_depth, execs_per_sec (float)
            for line in lines[len(lines) - number_of_interesting_lines:]:
                numbers = line.split(", ")

                Logger.log("checking for saturation in line " + str(numbers) + "\n", verbosity_level="debug")
                # we are interested in cycles_done ([1]), pending_totals ([4]) and pendings_favs ([5])
                cycles = int(numbers[1])
                pending_totals = int(numbers[4])
                pending_favs = int(numbers[5])
                Logger.log("cycles: " + str(cycles) + " pending_totals: " + str(pending_totals) +
                           " pending_favs: " + str(pending_favs) + "\n", verbosity_level="debug")

                self.saturation_index = self.saturation_index + (cycles * 2) + pending_favs + pending_totals
                Logger.log("saturation index is " + str(self.saturation_index) + "\n", verbosity_level="debug")

                if self.saturation_index > 3:
                    saturated = True
                    break

        return saturated

    def wait_for_stopping_conditions(self, fuzztime, outdir: str):
        # Depending on flipper, either time.sleep or time.sleep till afl_saturates

        Logger.log("waiting for stopping conditions for outdir " +
                   outdir + " and fuzztime " + str(fuzztime) + "\n", verbosity_level="debug")

        if not self.flipper_mode:
            Logger.log("non flipper mode -> just sleep\n", verbosity_level="debug")
            time.sleep(fuzztime)
        else:
            SATURATION_CHECK_PERIOD = 5 # default afl PLOT_UPDATE_SEC value
            for i in range(0, int(fuzztime/SATURATION_CHECK_PERIOD)):
                time.sleep(SATURATION_CHECK_PERIOD)
                if self.afl_saturated(outdir):
                    Logger.log("saturation detected\n", verbosity_level="debug")
                    break
            # sleep remaining time (if any)
            time.sleep(fuzztime % SATURATION_CHECK_PERIOD)

            # saturation reached
            self.already_processed_lines = 1 # first line is text, so not interesting -> initial value 1
            self.saturation_index = 0

    def execute_afl_fuzz(self, cgroup, functionname, outdir, fuzztime):
        errordir = path.join(outdir, "macke_errors")
        # This creates outdir + error dir
        makedirs(errordir)

        outfd = open(path.join(outdir, "output.txt"), "w")
        #TODO: Optional: Run parallel afl_cov to gather coverage stats
        #TODO: see if we can reuse ASAN coverage
        #TODO: check if we can use -M/-S
        proc = cgroups_Popen([AFLFUZZ, "-i", self.inputforfunc[functionname], "-o", outdir, "-m", "none",
                              self.afltarget, "--fuzz-driver=" + functionname], cgroup=cgroup, stdout=outfd, stderr=outfd)

        # Run saturation check
        self.wait_for_stopping_conditions(fuzztime, outdir)
        Logger.log("AFL saturated\n", verbosity_level="debug")

        try:
            kill(proc.pid, signal.SIGINT)
            # wait for afl-fuzz to cleanup
            proc.wait()
        except OSError:
            pass
        outfd.close()

        # afl-fuzz sometimes does not cleanup the target correctly, do it here
        try:
            pidstr = subprocess.check_output(["pgrep", "-x", "-f", self.afltarget + " --fuzz-driver=" + functionname]).decode("ascii")
            pids = pidstr.split()
            for pid in pids:
                try:
                    kill(int(pid), signal.SIGKILL)
                except OSError:
                    pass
        except subprocess.CalledProcessError as ex:
            pass

        return FuzzResult(self, cgroup, functionname, errordir, outdir);


    def execute_afl_tmin(self, cgroup, inputfile, outputfile, functionname):
        asan_env = environ.copy()
        asan_env["AFL_USE_ASAN"] = "1"
        return cgroups_run_checked_silent_subprocess([AFLTMIN, "-e", "-t", "50", "-i", inputfile, "-o", outputfile, "-m", "none", "--", self.minimizer, "--fuzz-driver=" + functionname], cgroup, env=asan_env)

    def minimize_crash(self, cgroup, crashinputfile, asanerror, function):
        minimized_name = path.join(path.dirname(crashinputfile), "min_" + path.basename(crashinputfile))
        # tmin fails on timeout - catch this case
        try:
            self.execute_afl_tmin(cgroup, crashinputfile, minimized_name, function)
            asanresult = self.execute_reproducer(cgroup, minimized_name, function)
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


        out = _run_checked_silent_subprocess([
            LLVMFUZZOPT, "-load", LIBMACKEFUZZOPT, "-generate-ktest", "-ktestfunction=" + function,
            "-ktestinputfile=" + inputfile] + kleeargflags + ["-ktestout=" + outfile, "-disable-output", self.orig_bcfile]);
