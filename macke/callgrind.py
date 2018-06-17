
"""
Module to run callgrind for a process call and receive line coverage
"""

import elftools.elf.elffile

import tempfile
from os import path
import os
import subprocess
import signal


from .config import VALGRIND



def get_cu_comp_dir(cu):
    die = cu.get_top_DIE()
    return die.attributes['DW_AT_comp_dir'].value.decode('ascii')

def retrieve_lines(objfile):
    fileline = dict()
    with open(objfile, 'rb') as f:
        elffile = elftools.elf.elffile.ELFFile(f)

        if not elffile.has_dwarf_info():
            print("File '" + objfile + "' has no DWARF info")

        dwarfinfo = elffile.get_dwarf_info()

        # Go over all the line programs in the DWARF information
        for CU in dwarfinfo.iter_CUs():
            lineprog = dwarfinfo.line_program_for_CU(CU)
            compdir = get_cu_comp_dir(CU)
            directories = lineprog['include_directory']

            for entry in lineprog.get_entries():
                # We're interested in those entries where a new state is assigned
                if entry.state is None:
                    continue

                line = entry.state.line
                # Line 0 means it can not be attributed to any line, thus ignore it
                if line == 0:
                    continue

                filenameentry = lineprog['file_entry'][entry.state.file -1]
                dir_index = filenameentry.dir_index
                filename = filenameentry.name.decode("ascii")

                directory = None if dir_index == 0 else directories[dir_index - 1].decode('ascii')

                filepath = compdir

                if directory:
                    filepath = path.join(filepath, directory)

                filepath = path.join(filepath, filename)


                if filepath not in fileline:
                    fileline[filepath] = set()
                fileline[filepath].add(line)

    # convert sets to lists
    ret = dict()
    for file, lines in fileline.items():
        ret[file] = list(lines)
    return ret


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("No argument given")
        sys.exit(0)
    lines = retrieve_lines(sys.argv[1])

    print(json.dumps(lines))

# constants
POSITION_SPECS = [ "ob", "fl", "fi", "fe", "fn", "cob", "cfi", "cfl", "cfn" ]

def parse_coverage(cov_file):
    content = cov_file.readlines()

    if not content:
        return dict()

    assert ((len(content) >= 3) and
            content[0] == "# callgrind format\n" and
            content[1] == "version: 1\n" and
            content[2].startswith("creator: callgrind-3"))

    i = 3
    while "positions" not in content[i]:
        i += 1
    assert content[i] == "positions: line\n"
    i += 1
    assert len(content) > i and content[i] == "events: Ir\n"

    extract = dict()
    fn_mapping = dict()
    fl_mapping = dict()

    # Skip until content
    while not any(content[i].startswith(pm) for pm in POSITION_SPECS):
        i += 1

    def parse_name(name_str, name_dict):
        if name_str[0] == '(':
            bracket_end = name_str.index(')')
            id = int(name_str[1:bracket_end])
            if id in name_dict:
                assert("(" + str(id) + ")\n" == name_str)
                return name_dict[id]
            else:
                assert("(" + str(id) + ")\n" != name_str)
                name_str = name_str[bracket_end+1:].strip()
                name_dict[id] = name_str
                return name_str
        else:
            return name_str

    currentline = 0
    currentfile = ""
    for line in content[i:]:
        if any(line.startswith(pm) for pm in POSITION_SPECS):
            pm = line[0:line.index('=')]

            if pm == "fl" or pm == "fi" or pm == "fe":
                currentfile = parse_name(line[3:], fl_mapping)
                if currentfile != "" and currentfile != "???" and currentfile not in extract:
                    extract[currentfile] = {'covered': set(), 'uncovered': set()}
            elif pm == "cfl" or pm == "cfi":
                parse_name(line[len(pm) + 1:], fl_mapping)
            elif pm == "ob" or pm == "cob":
                pass
            else:
                parse_name(line[len(pm) + 1:], fn_mapping)

        # Start with number
        elif '0' <= line[0] <= '9':
            # Line with details for the current file
            cols = line.split()
            loc = int(cols[0])
            if loc != 0 and currentfile != "" and currentfile != "???":
                assert int(cols[1]) != 0
                # This line was covered
                extract[currentfile]['covered'].add(loc)
            currentline = loc
        # Subposition compression
        elif line[0] == "+" or line[0] == "-":
            # Line with details for the current file
            cols = line.split()
            loc = currentline + int(cols[0])
            if loc != 0 and currentfile != "" and currentfile != "???":
                assert int(cols[1]) != 0
                # This line was covered
                extract[currentfile]['covered'].add(loc)
            currentline = loc
        # means cost on same line, thus nothing new is covered
        elif line[0] == "*":
            pass
        elif line.startswith("calls="):
            pass
        elif not line.strip():
            # Ignore empty lines
            pass
        elif line.startswith("totals:"):
            pass
        else:
            raise ValueError("Invalid line %s" % line)
    return extract


def get_coverage(args, inputfile, timeout=1):
    fd, tmpfilename = tempfile.mkstemp(prefix="macke_callgrind_")
    os.close(fd)
    infd = open(inputfile, "r")
    p = subprocess.Popen([ VALGRIND, "--tool=callgrind", "--callgrind-out-file=" + tmpfilename] + args, stdin=infd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    output = b""
    err = b""
    try:
        while p.poll() is None:
            (o, e) = p.communicate(None, timeout=1)
            output += o
            err += e
    # On hangup terminate the program
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            o, e = p.communicate(timeout=1)
        # If program does not like to be terminated, kill it.
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            # Timeout to get instead throw exception instead of just idling forever
            o, e = p.communicate(timeout=1)
        output += o
        err += e
    infd.close()

    with open(tmpfilename, 'r') as tmpfile:
        ret = parse_coverage(tmpfile)
    os.unlink(tmpfilename)
    return ret
