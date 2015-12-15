from clang.cindex import Index, CursorKind
from pprint import pprint
import os, glob

from optparse import OptionParser
import clang.cindex
import hashlib

global conditionals
global orig_file
global mod_file
global orig_lines
global mod_lines

def get_ifs_and_whiles(node):
    ch = [c for c in node.get_children()]
    if node.kind==CursorKind.IF_STMT or node.kind==CursorKind.WHILE_STMT or node.kind==CursorKind.DO_STMT or node.kind==CursorKind.FOR_STMT:
        conditionals.append(node)

    for c in ch:
        get_ifs_and_whiles(c)

def get_children_list(node):
    ch_list = []

    for c in node.get_children():
        ch_list.append(c)
    
    return ch_list

def get_compound_line(line_n):
    global orig_lines

    new_line = '{' + orig_lines[line_n-1].strip() + '}\n'

    return new_line

def add_instrumentation():
    global conditionals

    for c in conditionals:
        if c.kind==CursorKind.DO_STMT:
            continue

        ch_list = get_children_list(c)
        
        for ch in ch_list[1:]:
            # Convert simple statements to compound statements
            if not ch.kind==CursorKind.COMPOUND_STMT and not c.kind==CursorKind.DO_STMT:
                mod_lines[ch.location.line - 1] = get_compound_line(ch.location.line)

            cur_line_n = ch.location.line-1
            while '{' not in mod_lines[cur_line_n]:
                cur_line_n += 1
            cur_line = mod_lines[cur_line_n]
            instrumentation  = 'printf("Going into %s\\n");\n'%(hashlib.sha1(str(ch.location.file)+' '+str(ch.location.line)).hexdigest()) 
            for i, char in enumerate(cur_line):
                if char=='{':
                    break
            cur_line = cur_line[:i+1] + instrumentation + cur_line[i+1:]
            mod_lines[cur_line_n] = cur_line

def run(c_src_filename):
    global conditionals, orig_file, mod_file
    global orig_lines, mod_lines
    index = Index.create()

    if not os.path.exists(c_src_filename):
        print 'Problem opening file: ' + c_src_filename
        return None

    orig_file = open(c_src_filename, 'r')
    mod_file = open(c_src_filename+'.instr', 'w+')

    orig_lines = orig_file.readlines()

    # Make the modified file the same as original file
    mod_lines = orig_lines
    
    tu = index.parse(c_src_filename)
    if not tu:
        print 'Unable to load input'
        return None

    # Get list of all if, while and for statements
    get_ifs_and_whiles(tu.cursor)

    # Add instrumentation for all branching statements
    add_instrumentation()

    mod_file.writelines(mod_lines)

    print [c.location.line for c in conditionals]

if __name__=='__main__':
    global opts
    global conditionals

    conditionals = []
    
    parser = OptionParser('usage: %prog [options] -c {source file name}')
    parser.add_option('-c', '--source', action='store', type='string', dest='c_src_filename', help='Source C filename')

    (opts, args) = parser.parse_args()
    c_src_filename = opts.c_src_filename

    run(c_src_filename)
