"""
Storage for all global constants
"""

# A list of flags used by KLEE runs
KLEEFLAGS = [
    "--allow-external-sym-calls",
    "--istats-write-interval=3600",
    "--libc=uclibc",
    "--max-memory=1000",
    "--only-output-states-covering-new",
    "--optimize",
    # "--output-module",  # Helpful for debugging
    "--output-source=false",  # Removing this is helpful for debugging
    "--posix-runtime",
    "--stats-write-interval=3600",
    "--watchdog"
]

# A list of file extensions for errors that can be prepended by phase two
ERRORFILEEXTENSIONS = [
    ".ptr.err", ".free.err", ".assert.err", ".div.err", ".macke.err", ".fuzz.err"]
