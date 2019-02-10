
"""
Logging used in debug mode
"""

import sys
import os


class Logger:
    """
    Logs data in debug mode
    """
    VERBOSITY_LEVELS = ["none", "error", "warning", "info", "debug"]
    accepted_verbosity_levels = []
    log_file = None

    @staticmethod
    def open(verbosity_level="error", filename=None):

        if verbosity_level not in Logger.VERBOSITY_LEVELS:
            sys.stderr.write("warning: Unaccepted verbosity level. Defaulting to 'info'\n")
            index = Logger.VERBOSITY_LEVELS.index("info")
        else:
            index = Logger.VERBOSITY_LEVELS.index(verbosity_level)

        Logger.accepted_verbosity_levels = Logger.VERBOSITY_LEVELS[: index + 1]

        if filename:
            Logger.log_file = open(filename, "w")
        else:
            # write to stdout
            Logger.log_file = sys.stdout

    @staticmethod
    def log(message: str, verbosity_level="info"):
        if verbosity_level in Logger.accepted_verbosity_levels:
            if verbosity_level is not "info":
                Logger.log_file.write("(" + verbosity_level + ") ")
            Logger.log_file.write("[" + str(os.getpid()) + "]: ")
            Logger.log_file.write(message)

    @staticmethod
    def close():
        if Logger.log_file is not sys.stdout:
            Logger.log_file.close()
