import sys
import os
import glob
from optparse import OptionParser, OptionGroup
import re

def find_matching_error(ptr_err_directory, culp_func, culp_line):
    if not ptr_err_directory.endswith('/'):
        ptr_err_directory = ptr_err_directory+'/'
    for ptr_err_filename in glob.glob(ptr_err_directory+'*.ptr.err'):
        ptr_err = open(ptr_err_filename, 'r')
        
        for line in ptr_err:
            if line.startswith('Stack:'):
                break

        if line=='':
            print('Something went wrong while reading the ptr.err file.')
            return False

        stack_lines = []
        for line in ptr_err:
            if line.startswith('Info:'):
                break
            stack_lines.append(line)

        if line=='':
            print('Something went wrong while reading the ptr.err file.')
            return False

        for l in stack_lines:
            #print l.strip()
            if culp_func in l: #and (':'+str(culp_line)) in l:
                return True

    return False

def get_culp_line(ptr_err_filename, culp_func):
    ptr_err = open(ptr_err_filename, 'r')
    
    for line in ptr_err:
        if line.startswith('Stack:'):
            break

    if line=='':
        print('Something went wrong while reading the ptr.err file.')
        return None

    stack_lines = []
    for line in ptr_err:
        if line.startswith('Info:'):
            break
        stack_lines.append(line)

    if line=='':
        print('Something went wrong while reading the ptr.err file.')
        return None

    for l in stack_lines:
        if culp_func in l:
            culp_line = int(l.split(':')[-1].strip())
            return culp_line

    print('The given function not found in the ptr.err file. Something went wrong.')
    return None

def get_culp_func(err_filename):
    err_file = open(err_filename, 'r')

    for line in err_file:
        if line.startswith('Stack:'):
            break

    if line=='':
        print('Something went wrong while reading the ptr.err file.')
        return None

    stack_lines = []
    for line in err_file:
        if line.startswith('Info:'):
            break
        stack_lines.append(line)

    if line=='':
        print('Something went wrong while reading the ptr.err file.')
        return None
    
    func_line = 0
    for i, l in enumerate(stack_lines):
        if '__user_main' in l:
            func_line = stack_lines[i-1]
            break
    
    #func_name = func_line.split('in')[1].split('(')[0].strip()
    func_name = func_line.strip().split()[2]
    return func_name

def find_ptr_errs(klee_out_dir):
    err_funcs = {}
    
    if not klee_out_dir.endswith('/'):
        klee_out_dir = klee_out_dir+'/'
    # Read all the *.ptr.err files
    for f in glob.glob(klee_out_dir+'*.ptr.err'):
        #print 'Reading pointer error from file: ' + f
        culp_func = get_culp_func(f)
        if culp_func==None:
            print('Returning None')
            return None
        
        if culp_func not in err_funcs:
            err_funcs[culp_func] = []
        err_funcs[culp_func].append((f, get_culp_line(f, culp_func)))

    return err_funcs
    
