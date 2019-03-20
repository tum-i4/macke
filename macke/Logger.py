
"""
Logging used in debug mode
"""

import sys
import os
import time
import shutil
import tempfile


class Logger:
    """
    Logs data in debug mode
    """
    VERBOSITY_LEVELS = ["none", "error", "warning", "info", "debug"]
    accepted_verbosity_levels = []
    log_file = None
    log_filename = None

    @staticmethod
    def open(verbosity_level="error", filename=None):

        if verbosity_level not in Logger.VERBOSITY_LEVELS:
            sys.stderr.write("warning: Unaccepted verbosity level. Defaulting to 'info'\n")
            index = Logger.VERBOSITY_LEVELS.index("info")
        else:
            index = Logger.VERBOSITY_LEVELS.index(verbosity_level)

        Logger.accepted_verbosity_levels = Logger.VERBOSITY_LEVELS[: index + 1]

        if filename:
            Logger.log_filename = filename
            #Logger.log_file = open(filename, "a+")
        else:
            # write to stdout
            Logger.log_filename = "STDOUT"
            #Logger.log_file = sys.stdout

    @staticmethod
    def openfile():
        if Logger.log_filename=="STDOUT":
            Logger.log_file = sys.stdout
        else:
            Logger.log_file = open(Logger.log_filename, "a+")

    @staticmethod
    def log(message: str, verbosity_level="info"):
        Logger.openfile()
        if verbosity_level in Logger.accepted_verbosity_levels:
            if verbosity_level is not "info":
                Logger.log_file.write("(" + verbosity_level + ") ")
            Logger.log_file.write("[" + str(os.getpid()) + "]: ")
            Logger.log_file.write(message)
        Logger.close()

    @staticmethod
    def close():
        if Logger.log_file is not sys.stdout:
            Logger.log_file.close()

class PlotDataLogger:
    '''
    Logs plot data for KLEE and AFL rounds
    '''

    def __init__(self, output_dir: str, klee_output_dir: str, fuzzer_output_dir: str):
        self.output_dir = output_dir
        self.klee_output_dir = klee_output_dir
        self.fuzzer_output_dir = fuzzer_output_dir

        if not os.path.exists(fuzzer_output_dir):
            os.makedirs(fuzzer_output_dir)

        self.coverage_list = {}
        self.written_coverage = []

    def write_coverage(self):
        sorted_keys = sorted(self.coverage_list.keys())
        #Logger.log("Writing coverage in " + self.output_dir + "/coverage.log\n", verbosity_level="debug")
        coverage_file = open(os.path.join(self.output_dir, "coverage.log"), "a+")
        for s in sorted_keys:
            if s in self.written_coverage:
                continue
            for tup in self.coverage_list[s]:
                coverage_file.write("%s, %s, %s, %d\n" % (time.ctime(s), tup[0], tup[1], tup[2]))
            self.written_coverage.append(s)
        coverage_file.close()

    def log_fuzzer_progress(self):
        if not os.path.exists(os.path.join(self.fuzzer_output_dir, "cov/id-delta-cov")):
            return []

        coverage_file = open(os.path.join(self.fuzzer_output_dir, "cov/id-delta-cov"), "r")
        new_covered = []

        for line in coverage_file:
            #Logger.log("delta coverage line: " + line + "\n", verbosity_level="debug")
            if line.startswith("#"):
                continue
            fields = line.strip().split(", ")
            """
            if not fields[2].startswith(self.PREFIXES[1]):
                continue
            """
            if not fields[3]=="line":
                continue
            #file_name = fields[2].split(self.PREFIXES[1])[-1]
            file_name = fields[2].strip()
            line_no = int(fields[4])
            #Logger.log("Logging fuzzer progress line " + line + "\n", verbosity_level="debug")

            if not(any([ (("AFL", os.path.basename(file_name), line_no) in v or
                          ("KLEE", os.path.basename(file_name), line_no) in v) for v in self.coverage_list.values() ])):
                new_covered.append(("AFL", os.path.basename(file_name), line_no))
            #else:
            #    Logger.log(line + "already in " + str(self.coverage_list.values()) + "\n", verbosity_level="debug")

        self.coverage_list[time.time()] = new_covered
        self.write_coverage()

    def log_klee_coverage(self):
        new_covered = []

        while (
                not os.path.exists(
                    os.path.join(self.klee_output_dir, "run.istats"))):  # Klee should have at least done something
            continue

        tmp_istats_dir = tempfile.mkdtemp()
        os.system("cp " + os.path.join(os.path.join(self.klee_output_dir, "run.istats") + " " + tmp_istats_dir))
        covered = self.parse_run_istats(os.path.join(tmp_istats_dir, "run.istats"))

        #Logger.log("log_klee_coverage: " + str(covered.keys()) + "\n", verbosity_level="debug")

        for k in covered.keys():
            if not k:
                #Logger.log("log_klee_coverage: covered keys contains None\n", verbosity_level="warning")
                continue
            #Logger.log("klee covered " + k + "\n", verbosity_level="debug")
            file_name = os.path.basename(k)
            for src in covered[k].keys():
                line_no = src

                if not (any([(("AFL", os.path.basename(file_name), line_no) in v or
                              ("KLEE", os.path.basename(file_name), line_no) in v) for v in
                             self.coverage_list.values()])):
                    new_covered.append(("KLEE", file_name, line_no))

        shutil.rmtree(tmp_istats_dir)

        """
            for f in glob.glob(klee_out_dir+"/*.cov"):
                cov_file = open(f, "r")
                for line in cov_file:
                    #file_name = line.strip().split(":")[0].split(self.PREFIXES[0])[-1]
                    file_name = line.strip().split(":")[0].strip()
                    line_no = int(line.strip().split(":")[-1])
                    if not(any([ (("AFL", os.path.basename(file_name), line_no) in v or ("KLEE", os.path.basename(file_name), line_no) in v) for v in self.coverage_list.values() ])):
                        new_covered.append(("KLEE", os.path.basename(file_name), line_no)) 
        """
        self.coverage_list[time.time()] = new_covered
        self.write_coverage()

    def parse_run_istats(self, istats_file):
        istats = open(istats_file)

        covered = {}

        cur_file = None

        for line in istats:
            if line.startswith("fl="):
                cur_file = line.split("=")[1].strip()
                continue

            tokens = line.split()
            if len(tokens) != 15:
                continue
            src, cov = int(tokens[1]), int(tokens[2])  # Read source-level coverage rather than LLVM level

            if (cov > 0):
                if cur_file not in covered.keys():  # The covered file is newly covered
                    covered[cur_file] = {}
                covered[cur_file][src] = cov
        return covered
