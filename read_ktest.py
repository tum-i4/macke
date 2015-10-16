import os, sys
import subprocess
import glob
import re
from generate_separate_unit import lookup_function_path
from clang.cindex import Index, CursorKind
import binascii

def read_ktest(ktest_path):
    sym_vars = {}
    
    if not ktest_path.endswith('.ktest'):
        print ktest_path
        print 'The filename is not a ktest file.\n'
        return sym_vars
   
    ktest_dir = os.path.dirname(ktest_path)
    if not ktest_dir.endswith('/'):
        ktest_dir = ktest_dir + '/'

    os.system('ktest-tool ' + ktest_path + ' > ' + ktest_dir + 'ktest.out')

    ktest = open(ktest_dir + 'ktest.out')
    content = ktest.readlines()
    i = 0

    while i<len(content):
        line = content[i]
        if line.startswith('object') and ('sym_var_' in line): # Read the next three lines
            tokens = line.strip().split()
            sym_var_name = tokens[-1].strip("'")
            
            i += 1
            line = content[i]
            tokens = line.strip().split()
            size = int(tokens[-1])

            i += 1
            line = content[i]
            tokens = line.strip().split()
            data = tokens[-1]

            sym_vars[sym_var_name] = (size, data)

        i += 1

    os.system('rm -f ' + ktest_dir + 'ktest.out')

    return sym_vars

def get_expected_buffer_decl_stmt(var_name, size, data, i):
    decl_stmt = 'char %s_%i[%i] = {'%(var_name, i, size)
    try:
        hex_vals = data.split('\\x')[1:]
        hex_vals = [h.strip("'") for h in hex_vals]
        #hex_vals = ''.join(hex_vals)
        ascii_vals = binascii.unhexlify(''.join(hex_vals))
        ascii_vals = list(ascii_vals)
        ascii_vals = [a for a in ascii_vals]
        for i, h in enumerate(hex_vals):
            decl_stmt += r"'\x" + h + r"'"
            if i+1<len(hex_vals):
                decl_stmt += r", "
        '''
        for i, a in enumerate(ascii_vals):
            decl_stmt += "'" + a + "'"
            if i+1<len(ascii_vals):
                decl_stmt += ", "
        '''
    except TypeError:
        #print 'Something went wrong while converting string to hex value\nContinuing.'
        decl_stmt = 'char %s_%i[%i] = {'%(var_name, i, size)
        for i in range(size):
            decl_stmt += r"'\x00'"
            if i+1<size:
                decl_stmt += r", "
    decl_stmt += "};\n"

    return decl_stmt

def get_comparison_stmt(ktests, sym_var_names):
    oracles = []
    comparison_stmt = ''
    
    for i, k in enumerate(ktests):
        temp_oracle = 'int comp_des_' + str(i) + ' = ('
        for j, s in enumerate(k.keys()):
            temp_oracle += '(memcmp(st_%s, %s_%i, sizeof(%s_%i))==0)'%(s, s, i, s, i)
            if j+1<len(k.keys()):
                temp_oracle += ' && '
        temp_oracle += ');\n'
        oracles.append(temp_oracle)

    no_comps = 'int no_comps = !('

    for i, k in enumerate(ktests):
        no_comps += 'comp_des_' + str(i)
        if i+1<len(ktests):
            no_comps += ' || '

    no_comps += ');\n'

    for o in oracles:
        comparison_stmt += o

    comparison_stmt += no_comps
    return comparison_stmt

def get_memcpy_stmt(sym_var_names):
    memcpy_stmt = '#include <string.h>\n//Change "actual_sym_var_k"s to the actual variable names passed to the function.\n'
    for s in sym_var_names:
        memcpy_stmt += '#define st_%s actual_%s\n'%(s, s)
        #memcpy_stmt += 'void* st_%s = malloc(sizeof(actual_%s));\n'%(s, s)
        #memcpy_stmt += 'memcpy(st_%s, actual_%s, sizeof(actual_%s));\n'%(s, s, s)
    return memcpy_stmt

def generate_assert_code(ktest_folder):
    print "Generating assert code from - " + ktest_folder
    if not ktest_folder.endswith('/'):
        ktest_folder += '/'

    ktests = []

    for ptrerr_file in glob.glob(ktest_folder + '*.ptr.err'):
        ktest_filename = ptrerr_file[:-7]+'ktest'
        ktests.append(read_ktest(ktest_filename))

    sym_var_names = []
    if not ktests==[]:
        for k in ktests[0].keys():
            sym_var_names.append(k)

    memcpy_stmt = get_memcpy_stmt(sym_var_names)
    buffer_decl_stmt = ''

    last_temp_buffer_decl_stmt = ''
    for i, ktest in enumerate(ktests):
        for s in ktest.keys():
            temp_buffer_decl_stmt = get_expected_buffer_decl_stmt(s, ktest[s][0], ktest[s][1], i)
            if temp_buffer_decl_stmt=='':
                temp_buffer_decl_stmt = last_temp_buffer_decl_stmt
            else:
                last_temp_buffer_decl_stmt = temp_buffer_decl_stmt
            buffer_decl_stmt += temp_buffer_decl_stmt

    comparison_stmt = get_comparison_stmt(ktests, sym_var_names)
    
    comparison_stmt += 'klee_assert(no_comps);\n'
    
    return memcpy_stmt, buffer_decl_stmt, comparison_stmt

def get_func_node(node, func_name):
    if node.spelling==func_name and node.kind==CursorKind.FUNCTION_DECL and str(node.location.file).endswith('.c'): # Don't look at the header files
        ch = [c for c in node.get_children()]
        for c in ch:
            if c.kind==CursorKind.COMPOUND_STMT:
                return node
    ch = [c for c in node.get_children()]
    for c in ch:
        func_node = get_func_node(c, func_name)
        if func_node:
            return func_node
    return None

def get_function_call(node, call_name):
    if node.kind==CursorKind.CALL_EXPR and node.spelling==call_name:
        return node.location.line
    else:
        ch = [c for c in node.get_children()]
        if ch==[]:
            return None
        for c in ch:
            child_contains = get_function_call(c, call_name)
            if child_contains:
                return child_contains
    return None

def get_lines_to_insert(files_funcs, call_name):
    lines = []
    for f in files_funcs:
        filename, func_name = f
        index = Index.create()
        try:
            tu = index.parse(filename)
            if not tu:
                parser.error('unable to load input: ' + filename)

            func_node = get_func_node(tu.cursor, func_name)
            if func_node:
                call_line = get_function_call(func_node, call_name)
                if call_line:
                    lines.append((filename, func_name, call_line))
                else:
                    print 'Problem with file: %s caller function: %s callee function: %s'%(filename, func_name, call_name)
        except Exception:
            print 'Problem with file: %s caller function: %s callee function: %s'%(filename, func_name, call_name)
            continue
    return lines

def read_caller_file(caller_filename):
    if not os.path.exists(caller_filename):
        return []
    caller_file = open(caller_filename, 'r')
    callers = []

    for line in caller_file:
        callers.append(line.strip())

    return callers

def get_container_file(src_dir, func_name):
    callee_file = ''
    callee_files = lookup_function_path(src_dir, func_name)
    if callee_files:
        callee_file = callee_files[0]
    else:
        return None
    re_pattern = src_dir + '(.*)_units/(.*)_'+func_name+'.c.callee'
    re_match = re.search(re_pattern, callee_file)
    c_filename = re_match.group(2)
    c_filename = src_dir+c_filename+'.c'

    return c_filename

def get_location_to_insert(ktest_folder):
    if not ktest_folder.endswith('/'):
        ktest_folder += '/'

    re_pattern = '/(.*)/(.*)_units/(.*)_(.*)/'
    re_match = re.search(re_pattern, ktest_folder)
    func_name_trimmed = re_match.group(4)
    func_name = func_name_trimmed

    units_dir = os.path.split(os.path.abspath(ktest_folder))[0]+'/'
    units_folder_name = os.path.split(os.path.abspath(units_dir))[1]
    re_pattern = '(.*)_units'
    re_match = re.search(re_pattern, units_folder_name)
    main_name = re_match.group(1)
    
    for u in glob.glob(units_dir+'*.c.units'):
        no_ext = u[:-8]
        if no_ext.endswith('_'+func_name_trimmed):
            re_pattern = units_dir + main_name + '_(.*).c.units'
            re_match = re.search(re_pattern, u)
            func_name = re_match.group(1)

    caller_filename = units_dir + main_name + '_' + func_name + '.c.caller'
    caller_list = read_caller_file(caller_filename)
    src_dir = os.path.split(os.path.abspath(units_dir))[0]+'/'

    functions = []
    for c in caller_list:
        container_file = get_container_file(src_dir, c)
        #Just playing around
        '''
        container_filename_only = os.path.split(os.path.abspath(container_file))[1]
        container_file_unit = container_file[:-2] + '_units/' + container_filename_only[:-2] + '_' + c + '.c.units'
        if os.path.isfile(container_file_unit):
            os.system('mv %s %s'%(container_file, container_file+'.bkp'))
            os.system('mv %s %s'%(container_file_unit, container_file))
        '''
        if not container_file:
            continue
        functions.append((container_file, c))
    
    lines_to_insert = get_lines_to_insert(functions, func_name)
    return lines_to_insert

def copy_and_modify_unit_file(unit_filename, line_n, assertion_code):
    print line_n
    memcpy_stmt, buffer_decl_stmt, comparison_stmt = assertion_code
    orig_file = open(unit_filename, 'r')
    copy_file = open(unit_filename+'.assert', 'w+')

    orig_file_tracker = 0
    for i, line in enumerate(orig_file):
        if orig_file_tracker+1==line_n:
            copy_file.write('/*\n')
            copy_file.write(memcpy_stmt)
            copy_file.write(buffer_decl_stmt)
            copy_file.write(comparison_stmt)
            copy_file.write('*/\n')
        if 'klee_make_symbolic' not in line:
            orig_file_tracker += 1
        
        copy_file.write(line)

    copy_file.close()
    orig_file.close()
    # os.system('mv %s %s'%(unit_filename+'.copy', unit_filename))

def modify_unit_files(locations_to_insert, assertion_code):
    for l in locations_to_insert:
        filepath, func_name, line_n = l
        src_dir, c_filename = os.path.split(os.path.abspath(filepath))
        unit_filename = '%s/%s_units/%s_%s.c.units'%(src_dir, c_filename[:-2], c_filename[:-2], func_name)
        copy_and_modify_unit_file(unit_filename, line_n, assertion_code)

if __name__=='__main__':
    ktest_folder = sys.argv[1]
    memcpy_stmt, buffer_decl_stmt, comparison_stmt = generate_assert_code(ktest_folder)
    print memcpy_stmt, buffer_decl_stmt, comparison_stmt
    assertion_code = (memcpy_stmt, buffer_decl_stmt, comparison_stmt)

    locations_to_insert = get_location_to_insert(ktest_folder)
    print locations_to_insert

    modify_unit_files(locations_to_insert, assertion_code)

