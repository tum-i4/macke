"""
Core class for MACKE execution.
Contains methods for both phases and some analysis
"""

import json
import shutil
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from os import makedirs, path
from macke.constants import UCLIBC_LIBS
from macke.config import (CONFIGFILE, get_current_git_hash,
                          get_klee_git_hash, get_llvm_opt_git_hash)
from macke.Klee import execute_klee


class Shamrock:
    """
    Main container for all steps of the MACKE analysis
    """

    def __init__(self, bitcodefile, comment="",
                 parentdir="/tmp/macke", quiet=False,
                 flags_user=None, posixflags=None, posix4main=None,
                 libraries = None):
        # Only accept valid files and directory
        assert path.isfile(bitcodefile)

        # store the path to the analyzed bitcode file
        self.bitcodefile = bitcodefile


        # add libraries to flags_user
        self.flags_user = []
        if libraries is not None:
            for l in libraries:
                if l not in UCLIBC_LIBS:
                    self.flags_user.append("-load=lib"+l+".so")

        # Store information from command line
        self.comment = comment
        self.flags_user += flags_user if flags_user is not None else []
        self.posixflags = posixflags if posixflags is not None else []
        self.posix4main = posix4main if posix4main is not None else []

        # generate name of directory with all run results
        self.starttime = datetime.now()
        newdirname = self.starttime.strftime("%Y-%m-%d-%H-%M-%S")
        self.rundir = path.join(parentdir, newdirname)
        self.parentdir = parentdir

        # Generate the path for the bitcode directory
        self.bcdir = path.join(self.rundir, "bitcode")

        # Generate the filename for the copy of the program
        self.program_bc = path.join(self.rundir, "bitcode", "program.bc")

        # Filename, where the index of the klee runs is stored
        self.kleejson = path.join(self.rundir, "klee.json")

        self.kleedir = path.join(self.rundir, "klee")
        self.kleeoutdir = path.join(self.kleedir, "klee-out-1")

        # Some attributes, that are filled later
        self.endtime = None

        # Setting quiet == True suppress all outputs
        self.quiet = quiet

    def generate_klee_json(self):
        """
        Generate a klee json containing the single klee run
        """
        info = dict({"klee-out-1": OrderedDict([
            ("bcfile", self.program_bc),
            ("folder", self.kleeoutdir),
            ("function", "main"),
            ("phase", 1),
        ])})

        with open(self.kleejson, 'w') as file:
            json.dump(info, file)

    def run_complete_analysis(self):
        """
        Run all consecutive steps of the analysis
        """

        self.run_initialization()
        self.run_klee()
        self.run_finalization()

    def run_initialization(self):
        """
        Initialize the SHAMROCK output directory
        """

        # Create an some empty directories
        makedirs(self.kleedir)
        makedirs(self.bcdir)

        # Copy the unmodified bitcode file
        shutil.copy2(self.bitcodefile, self.program_bc)

        # Copy macke's config file
        shutil.copy2(CONFIGFILE, self.rundir)

        self.generate_klee_json()

        # Store some basic information about the current run
        with open(path.join(self.rundir, "info.json"), 'w') as file:
            info = OrderedDict()
            info["macke-git-version-hash"] = get_current_git_hash()
            info["llvm-opt-git-version-hash"] = get_llvm_opt_git_hash()
            info["klee-git-version-hash"] = get_klee_git_hash()
            info["analyzed-bitcodefile"] = path.abspath(self.bitcodefile)
            info["run-argv"] = sys.argv
            info["shamrock"] = "This is a pure KLEE analysis of main"
            info["comment"] = self.comment
            json.dump(info, file)

        self.qprint("Analysis started at %s" % self.starttime)
        self.qprint("KLEE Timeout set to %s" %
                    (self.starttime + timedelta(
                        seconds=int(self.flags_user[0][len("--max-time="):]))))

    def run_klee(self):
        """
        Run KLEE on the given program
        """
        execute_klee(
            self.program_bc, "main", self.kleeoutdir, flags=self.flags_user,
            posixflags=self.posixflags, posix4main=self.posix4main)

    def run_finalization(self):
        """
        Print a summary and write the result to the MACKE directory
        """
        self.endtime = datetime.now()

        # Export all the data gathered so far to a json file
        with open(path.join(self.rundir, "timing.json"), 'w') as file:
            info = OrderedDict()

            info["start"] = self.starttime.isoformat()
            info["start-phase-two"] = self.endtime.isoformat()
            info["end"] = self.endtime.isoformat()

            json.dump(info, file)

        self.qprint("Analysis ended at   %s" % self.endtime)

    def qprint(self, *args, **kwargs):
        """
        Call pythons print, if MACKE is not set to be quiet
        """
        if not self.quiet:
            print(*args, **kwargs)
