"""
Load global configurations, if they exist in a config.ini file
"""

import configparser
import os

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), "..", "config.ini"))

LIBMACKEOPT = CONFIG.get("binaries", "libmackeopt")
LLVMOPT = CONFIG.get("binaries", "llvmopt", fallback="opt")
