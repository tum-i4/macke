import sys, os
import glob
import struct 

from .config import KLEEBIN
from .Logger import Logger

# Copied from JOLF and adapted

version_no = 3
TESTCASE_I = 0

class KTest:
    @staticmethod
    def fromfile(path):
        if not os.path.exists(path):
            print("ERROR: file %s not found" % (path))
            sys.exit(1)
            
        f = open(path,'rb')
        hdr = f.read(5)
        if len(hdr)!=5 or (hdr!=b'KTEST' and hdr != b"BOUT\n"):
            raise Exception('unrecognized file')
        version, = struct.unpack('>i', f.read(4))
        if version > version_no:
            raise Exception('unrecognized version')
        numArgs, = struct.unpack('>i', f.read(4))
        args = []
        for i in range(numArgs):
            size, = struct.unpack('>i', f.read(4))
            args.append(str(f.read(size).decode(encoding='ascii')))
            
        if version >= 2:
            symArgvs, = struct.unpack('>i', f.read(4))
            symArgvLen, = struct.unpack('>i', f.read(4))
        else:
            symArgvs = 0
            symArgvLen = 0

        numObjects, = struct.unpack('>i', f.read(4))
        objects = []
        for i in range(numObjects):
            size, = struct.unpack('>i', f.read(4))
            name = f.read(size)
            size, = struct.unpack('>i', f.read(4))
            bytes = f.read(size)
            objects.append( (name,bytes) )

        # Create an instance
        b = KTest(version, args, symArgvs, symArgvLen, objects)
        # Augment with extra filename field
        b.filename = path
        return b
    
    def __init__(self, version, args, symArgvs, symArgvLen, objects):
        self.version = version
        self.symArgvs = symArgvs
        self.symArgvLen = symArgvLen
        self.args = args
        self.objects = objects

        # add a field that represents the name of the program used to
        # generate this .ktest file:
        program_full_path = self.args[0]
        program_name = os.path.basename(program_full_path)
        # sometimes program names end in .bc, so strip them
        if program_name.endswith('.bc'):
          program_name = program_name[:-3]
        self.programName = program_name

def trimZeros(str):
    original_length = len(str)
    for i in range(len(str)):
        if str[i]!=0:
            str = str[i:]
            break

    for i in range(len(str))[::-1]:
        if str[i]!=0:
            str = str[:i+1]
            break

    if (original_length == len(str)) and (str[0]==0):
        return b''
    
    return str 

def read_text(filename):
    f = open(filename, "r")
    return f.readline()

def combine_args_and_stdin(out_folder):
    if os.path.isdir(out_folder + "/args") and os.path.isdir(out_folder + "/stdin"):
        if not os.path.isdir(out_folder + "/combined"):
            os.system("mkdir %s/combined" % (out_folder))
        for f in glob.glob(out_folder + "/args/*.txt"):
            stdin_path = out_folder + "/stdin/" + os.path.basename(f)[:-3] + "stdin.txt"
            if os.path.exists(stdin_path):
                combined_text = read_text(f) + " " + read_text(stdin_path)
            else:
                combined_text = read_text(f)
            combined_textfile = open(out_folder + "/combined/" + os.path.basename(f), "w")
            combined_textfile.write(combined_text)
            combined_textfile.close()
    else:
        print("Nothing to combine at %s"%(out_folder))

def read_ktest_to_text(ktest_filename):
    if not os.path.exists(ktest_filename):
        print("ERROR: Path to the ktest file does not exist.")
        return None

    ktest_basename = os.path.basename(ktest_filename)
    os.system("%sktest-tool --write-ints %s > /tmp/%s.txt" % (KLEEBIN, ktest_filename, ktest_basename))

    ktest_textfile = open("/tmp/%s.txt" % (ktest_basename), "r")
    return ktest_textfile.readlines()

def parse_meta_block(ktest_text):
    meta_block = []
    for line in ktest_text:
        value = line.split(":")[-1].strip().strip("'")
        meta_block.append(value)
    return meta_block

def parse_object_block(ktest_text):
    object_block = []

    for line in ktest_text:
        value = line.split(":")[-1].strip().strip("'")
        object_block.append(value)
    return object_block

def parse_ktest(ktest_text):
    meta = []
    objects = []

    n_lines = len(ktest_text)
    i = 0

    while i < n_lines:
        if ktest_text[i].startswith("ktest_file"):
            meta.append(parse_meta_block(ktest_text[i:i + 3]))
            i += 2
        elif ktest_text[i].startswith("object"):
            objects.append(parse_object_block(ktest_text[i:i + 3]))
            i += 2
        i += 1
    return meta, objects

def get_object_type(o):
    name_line = o[0].decode("utf-8")

    if name_line.startswith("n_args"):
        return "n_args"
    elif name_line.startswith("arg"):
        return "arg"
    elif name_line.endswith("-data"):
        return "file"
    elif name_line.endswith("-data-stat"):
        return "file-stat"
    elif name_line.startswith("stdin"):
        return "stdin"
    elif name_line.startswith("stdin-stat"):
        return "stdin-stat"
    elif name_line.startswith("model_version"):
        return "model"
    elif name_line.startswith("stdout"):
        return "stdout"

    return name_line

def get_n_args(o):
    name = o[0]
    size = int(o[1])
    data = o[2]
    return name, size, data

def get_full_arg(o):
    name = o[0].decode("utf-8")
    size = int(o[1])
    data = o[2]
    #data = str(o[2]).split("\\x0")[0]
    return name, size, data

def get_full_stdin(o):
    return get_full_arg(o)

def get_full_stdin_stat(o):
    return get_full_arg(o)

def get_full_file(o):
    name = o[0].decode("utf-8")
    size = int(o[1])
    data = o[2]
    return name, size, data

def get_full_file_stat(o):
    return get_full_arg(o) 

def get_full_model_version(o):
    return get_n_args(o)

def write_stdin_to_file(testname, objects, out_folder):
    o_with_content = []
    for o in objects:
        if not o[2] == "":
            o_with_content.append(o)

    if o_with_content:
        if not os.path.isdir("%s/stdin" % (out_folder)):
            os.system("mkdir %s/stdin" % (out_folder))

    for o in o_with_content:
        if o[2] == "":
            continue
        testcase = open("%s/stdin/%s.%s.txt" % (out_folder, testname, o[0]), "w")
        testcase.write(o[2])
        testcase.close()

def write_files_to_file(testname, objects, out_folder):
    o_with_content = []
    for o in objects:
        if not o[2] == "":
            o_with_content.append(o)

    """
    if o_with_content:
        if not os.path.isdir("%s/files" % (out_folder)):
            os.system("mkdir %s/files" % (out_folder))
    """
    for o in o_with_content:
        if o[2] == "":
            continue
        testcase = open("%s/%s.%s.txt" % (out_folder, testname, o[0]), "w")
        testcase.write(o[2])
        testcase.close()

def write_args_to_file(testname, objects, out_folder):
    if not os.path.isdir("%s/args" % (out_folder)):
        os.system("mkdir %s/args" % (out_folder))
    testcase = open("%s/args/%s.txt" % (out_folder, testname), "w")
    arg_string = ""
    for o in objects:
        arg_string += o[2] + " "
    if arg_string != "":
        arg_string += "\n"
        testcase.write(arg_string)

def write_testcase_file(testname, objects, out_folder):
    command_args_objects = []
    file_objects = []
    stdin_objects = []

    Logger.log("write_testcase_file " + testname + " " + str(objects) + " " + out_folder + "\n", verbosity_level="debug")

    for o in objects:
        type = get_object_type(o)
        if type == "n_args":
            name, size, data = get_n_args(o)
        elif type == "arg":
            name, size, data = get_full_arg(o)
            #command_args_objects.append([name, size, data])
            command_args_objects.append(data)
        elif type == "file":
            name, size, data = get_full_file(o)
            file_objects.append([name, size, data])
        elif type == "file-stat":
            name, size, data = get_full_file_stat(o)
        elif type == "stdin":
            name, size, data = get_full_stdin(o)
            stdin_objects.append([name, size, data])
        elif type == "stdin-stat":
            name, size, data = get_full_stdin_stat(o)
        elif type == "model":
            name, size, data = get_full_model_version(o)
        elif type == "stdout":
            pass
        else:
            print(testname)
            print("Invalid type '%s' read. Ending in panic" % (type))
            sys.exit(-1)

    if not os.path.isdir(out_folder):
        os.system("mkdir %s" % (out_folder))
    #write_args_to_file(testname, command_args_objects, out_folder)
    write_files_to_file(testname, file_objects, out_folder)
    #write_stdin_to_file(testname, stdin_objects, out_folder)
    ret = ""
    for arg in command_args_objects:
        if arg not in ["A", "B"]:
            ret += " " + arg
    return ret 

def parse_ktest_object(ktest):
    objects = []

    for i,(name,data) in enumerate(ktest.objects):
        str = trimZeros(data)
        str = str.decode("utf-8", errors="ignore")
        objects.append([name, len(str), str])

    return [], objects

def process_file(ktest_filename):
    # print(ktest_filename)
    #ktest_text = read_ktest_to_text(ktest_filename)
    Logger.log("Processing ktest file " + ktest_filename + "\n", verbosity_level="debug")
    ktest = KTest.fromfile(ktest_filename) 
    if not ktest:
        print("Ending in panic.")
        sys.exit(-1)

    #meta, objects = parse_ktest(ktest_text)
    meta, objects = parse_ktest_object(ktest)

    return meta, objects

def process_klee_out(klee_out_name, out_folder):
    global TESTCASE_I
    argv = []
    Logger.log("Reading all ktest files in " + klee_out_name + "\n", verbosity_level="debug")
    for t in glob.glob("%s/*.ktest" % (klee_out_name)):
        meta, objects = process_file(t)
        testcase_basename = os.path.basename(t).split(".")[0]
        ret = write_testcase_file(testcase_basename, objects, out_folder)
        if ret:
            argv.append(ret)
        TESTCASE_I += 1

    return argv

def process_all_klee_outs(parent_dir, out_folder):
    print("Reading all klee-out-* from: %s" % (parent_dir))
    for f in glob.glob("%s/klee-out-*/" % (parent_dir)):
        process_klee_out(f, out_folder)

def main(parent_dir, out_dir):
    ktest_list = glob.glob("%s/*.ktest" % (parent_dir))
    if not ktest_list:
        process_all_klee_outs(parent_dir, out_dir)
    else:
        process_klee_out(parent_dir, out_dir)
    combine_args_and_stdin(out_dir)

if __name__=="__main__":
    if len(sys.argv) == 3:
        klee_out = sys.argv[1]
        out_folder = sys.argv[2]
    elif len(sys.argv) == 2:
        klee_out = sys.argv[1]
        if not os.path.isdir("/tmp/testcases"):
            os.system("mkdir /tmp/testcases")
        out_folder = "/tmp/testcases"
    else:
        print("%d arguments given." % (len(sys.argv)))
        print(sys.argv)
        print("Correct usage: read_klee_testcases.py <klee-out-folder> [testcase output folder]")
        sys.exit(-1)

    main(klee_out, out_folder)

