"""
Storage for all global constants
"""

# A list of flags used by KLEE runs
KLEEFLAGS = [
    "--allow-external-sym-calls",
    "--libc=uclibc",
    "--max-memory=1000",
    "--only-output-states-covering-new",
    "--optimize",
    "--disable-inlining",
    # "--output-module",  # Helpful for debugging
    "--output-source=false",  # Removing this is helpful for debugging
    "--posix-runtime",
    #"--watchdog"
]

UCLIBC_LIBS = [
    "acl", "crypt", "dl", "m", "pthread", "rt", "selinux"
]

FUZZFUNCDIR_PREFIX = "fuzz_out_"

# A list of file extensions for errors that can be prepended by phase two
ERRORFILEEXTENSIONS = [
    ".ptr.err", ".free.err", ".assert.err", ".div.err", ".macke.err", ".fuzz.err"]
