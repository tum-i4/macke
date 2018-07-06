
"""
Module to contain cgroup abstractions
"""

from os import path, killpg, getpgid, setsid
import os
import errno
import subprocess
import signal

from .config import FUZZMEMLIMIT, THREADNUM

_limitfilenames = [ "memory.limit_in_bytes", "memory.memsw.limit_in_bytes" ]

def get_num_threads():
    # Same behaviour as the multiprocessing.Pool for THREADNUM
    if THREADNUM is None:
        return os.cpu_count()
    return THREADNUM


def get_cgroups():
    """
    Return names of all cgroups
    """
    num_groups = get_num_threads()

    ret = []
    for i in range(num_groups):
        ret.append("mackefuzzer_" + str(i))
    return ret


def initialize_cgroups(usergroup, ignore_swap):
    """
    Creates and initiliazes one group for each thread
    """
    num_groups = get_num_threads()
    limitstr = str(FUZZMEMLIMIT) + "M"
    files = _limitfilenames

    for cgrpname in get_cgroups():
        subprocess.check_call(["cgcreate", "-s", "775", "-d", "775", "-f", "775", "-a", usergroup, "-t", usergroup, "-g", "memory:" + cgrpname])
        cpath = path.join("/sys/fs/cgroup/memory", cgrpname)
        for p in _limitfilenames:
            fpath = path.join(cpath, p)
            if not path.exists(fpath) and path.basename(fpath) == "memory.memsw.limit_in_bytes":
                if not ignore_swap:
                    print("Your system does not allow limiting swap memory with cgroups. Either disable swap or continue at your own risk with by adding --ignore-swap to initialization and execution")
                    return False
                else:
                    continue
            with open(fpath, 'w') as f:
                f.write(limitstr)
    return True

def validate_cgroups(ignore_swap):
    """
    Validate whether cgroups are present and we have access to it
    """
    num_groups = get_num_threads()

    required_limit = FUZZMEMLIMIT * 1024 * 1024

    for cgrpname in get_cgroups():
        cpath = path.join("/sys/fs/cgroup/memory", cgrpname)
        if not path.exists(cpath):
            print("Some required groups do not exist")
            return False

        if not os.access(cpath, os.R_OK | os.W_OK | os.X_OK):
            print("Lacking access to groups")
            return False
        for p in _limitfilenames:
            fpath = path.join(cpath, p)
            if not path.exists(fpath) and path.basename(fpath) == "memory.memsw.limit_in_bytes":
                if not ignore_swap:
                    print("Your system does not allow limiting swap memory with cgroups. Either disable swap or continue at your own risk with by adding --ignore-swap to initialization and execution")
                    return False
                else:
                    continue
            with open(fpath, 'r') as f:
                limit = int(f.read())
                if limit != required_limit:
                    print("Some cgroups contain invalid memory limits")
                    return False
    return True


def cgroups_run_checked_silent_subprocess(args, cgroup, **kwargs):
    return subprocess.check_output(["cgexec", "-g", "memory:" + cgroup, "--sticky" ] + args, stderr=subprocess.STDOUT, **kwargs)

def cgroups_run_subprocess(command, *args, cgroup=None, **kwargs):
    if cgroup is None:
        raise ValueError("No cgroup given")
    return subprocess.check_output(["cgexec", "-g", "memory:" + cgroup, "--sticky" ] + command, *args, **kwargs, stderr=subprocess.STDOUT)


def cgroups_Popen(command, *args, cgroup=None, **kwargs):
    if cgroup is None:
        raise ValueError("No cgroup given")
    return subprocess.Popen(["cgexec", "-g", "memory:" + cgroup, "--sticky" ] + command, *args, **kwargs)


def cgroups_run_timed_subprocess(command, *args, cgroup=None, timeout=1, **kwargs):
    """
    Starts a subprocess, waits for it and returns (exitcode, output, erroutput)
    """
    if cgroup is None:
        raise ValueError("No cgroup given")
    p = cgroups_Popen(command, *args, cgroup=cgroup, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=setsid)
    output = b""
    err = b""
    try:
        while p.poll() is None:
            (o, e) = p.communicate(None, timeout=timeout)
            output += o
            err += e
    # On hangup kill the program (and children)
    except subprocess.TimeoutExpired:
        killpg(getpgid(p.pid), signal.SIGKILL)

    return p.returncode, output, err
