"""
All logic to read informations from KLEE's run.istats file
"""


def extract_linecoverage(run_istats_file):
    content = []
    with open(run_istats_file, 'r') as f:
        content = f.readlines()

    # Check, if the output format matches the format
    assert(len(content) > 10)
    assert(content[0] == 'version: 1\n')
    assert(content[1] == 'creator: klee\n')
    assert(content[6] == 'positions: instr line\n')

    extract = dict()
    currentfile = ""

    # Skip the header and read the rest
    for line in content[22:]:
        if '0' <= line[0] <= '9':
            # Line with details for the current file
            cols = line.split()
            loc = int(cols[1])
            if loc != 0 and currentfile != "":
                if int(cols[2]) != 0:
                    # This line was covered
                    extract[currentfile]['covered'].add(loc)
                else:
                    # This line was not covered
                    extract[currentfile]['uncovered'].add(loc)
        elif line.startswith("fl="):
            # Line with information about a file
            currentfile = line[3:].strip()
            if currentfile != "":
                extract[currentfile] = {'covered': set(), 'uncovered': set()}
        elif line.startswith("fn="):
            # Line with information about a function name
            pass
        elif line.startswith("cfl="):
            # Line with the file name of a called function
            pass
        elif line.startswith("cfn="):
            # Line with the name of a called function
            pass
        elif line.startswith("calls="):
            # Line with informations about a call instruction
            pass
        else:
            raise ValueError("Invalid line %s" % line)

    result = dict()
    for file, lines in extract.items():
        if not any(excludes in file for excludes in {
                "/libc/string/",
                "/runtime/Intrinsic/",
                "/runtime/POSIX/",
                "/libc/termios/",
                "/libc/stdio/",
                "/libc/stdlib/",
                "/klee-uclibc/"}):
            result[file] = lines

    return result
