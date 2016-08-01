'''
A utility to generate a unit test case for a given C function. 
Works by generating symbolic parameters for the function using KLEE and replacing main function
'''
from .branch_analyzer import analyze
from .callee import get_callee_list

from clang.cindex import Index, CursorKind
from pprint import pprint
import sys, os
import re
import glob

from optparse import OptionParser, OptionGroup
import clang.cindex

global func_nodes
global decl_vars

class Expr:
    def __init__(self, location, iden, datatype):
        self.line = location.line
        self.iden = iden
        self.datatype = datatype

    def __str__(self):
        return str(self.line) + ': ' + self.iden + ': ' + self.datatype

    def __repr__(self):
        return str(self.line) + ': ' + self.iden + ': ' + self.datatype

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if self.line==other.line and self.iden==other.iden and self.datatype==other.datatype:
            return True
        else:
            return False

    def __lt__(self, other):
        if self.line<other.line:
            return True
        else:
            return False
g_sym_var_count = 0

def lookup_function_path(src_root, func_name):
    if not os.path.isdir(src_root):
        print('That is an invalid source root directory.')
        return None

    possible_fs = glob.glob(src_root+'*_units/*_'+func_name+'.c.callee')
    
    return possible_fs

def inject_symbolic_code(orig_fl_name, prob_exprs):
    global sym_table
    expr_i = 0
    orig_fl = open(orig_fl_name, 'r')
    instr_fl = open(orig_fl_name+'.instr', 'w')
    
    for orig_i, line in enumerate(orig_fl):
        instr_fl.write(line)
        while expr_i<len(prob_exprs) and orig_i==prob_exprs[expr_i].line:
            to_paste = generate_sym_code(prob_exprs[expr_i])
            instr_fl.write('// ' + to_paste)
            expr_i += 1
        '''
        only_exprs = [e.iden for e in prob_exprs]
        if expr_i<len(prob_exprs):
            to_lookup = only_exprs[expr_i][:only_exprs[expr_i].find('->')] if '->' in only_exprs[expr_i] else only_exprs[expr_i]
        while expr_i<len(prob_exprs) and sym_table[to_lookup]==orig_i+1:
            to_paste = generate_sym_code(prob_exprs[expr_i])
            instr_fl.write(to_paste)
            expr_i += 1
            if expr_i<len(prob_exprs):
                to_lookup = only_exprs[expr_i][:only_exprs[expr_i].find('->')] if '->' in only_exprs[expr_i] else only_exprs[expr_i]
        '''
    instr_fl.close()

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

def get_cursor_id(cursor, cursor_list = []):
    return None

    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i,c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1

def get_info(node, depth=0):
    global prob_exprs
    global prob_lines
    children = [get_info(c, depth+1)
                    for c in node.get_children()]
    return { 'id' : get_cursor_id(node),
         'kind' : node.kind,
         'type' : node.type.spelling,
         'usr' : node.get_usr(),
         'spelling' : node.spelling,
         'location' : node.location,
         'extent.start' : node.extent.start,
         'extent.end' : node.extent.end,
         'is_definition' : node.is_definition(),
         'definition id' : get_cursor_id(node.get_definition()),
         'children' : children }

def generate_sym_code(expr):
    global g_sym_var_count
    param1 = ''
    if expr.datatype.endswith('*'):
        datatype = expr.datatype[:-1].strip()
        param1 = '%s'%expr.iden
        if datatype.lower()=='char' or datatype.lower()=='const char': # special case of char pointers
            code_str = ('klee_make_symbolic(%s, sizeof(char)*100, "sym_var_%i");\n')%(param1, g_sym_var_count)
            g_sym_var_count += 1
            return code_str
    else:
        datatype = expr.datatype.strip()
        param1 = '&%s'%expr.iden
    code_str = ('klee_make_symbolic(%s, sizeof(%s), "sym_var_%i");\n')%(param1, datatype, g_sym_var_count)
    g_sym_var_count += 1
    return code_str

def find_func_node(node, func_name):
    ch = [c for c in node.get_children()]
    kinds = [c.kind for c in ch]
    if node.kind==CursorKind.FUNCTION_DECL and node.spelling==func_name and str(node.location.file).endswith('.c') and (CursorKind.COMPOUND_STMT in kinds): # Don't look at the header files or just declarations, but full definitions
        return node
    else:
        ch = [c for c in node.get_children()]
        if ch==[]:
            return None
        for c in ch:
            func_node = find_func_node(c, func_name)
            if func_node:
                return func_node

    return None

def copy_all_minus_main(orig_fl, node, prob_exprs):
    global g_sym_var_count
    
    to_insert = {}
    for e in prob_exprs:
        param1 = ''
        if e[2].endswith('*'):
            datatype = e[2][:-1].strip()
            param1 = '%s'%e[1]
        else:
            datatype = e[2].strip()
            param1 = '&%s'%e[1]
        code_str = ('// klee_make_symbolic(%s, sizeof(%s), "sym_var_%i");// Please take care of allocating memory in case of pointers or structures\n')%(param1, datatype, g_sym_var_count)
        g_sym_var_count += 1
        to_insert[e[0]] = code_str
    
    main_node = find_func_node(node, 'main')
    if main_node:
        main_start, main_end = main_node.extent.start.line, main_node.extent.end.line
    else:
        main_start, main_end = -1, -2
    copy_main = '#include <klee/klee.h> // Generated code - Unit testing framework\n'
    expr_i = 0
    for i, line in enumerate(orig_fl):
        if i+1 not in list(range(main_start, main_end+1)):
            copy_main = copy_main + line
            # copy_fl.write(line)
            if i+1 in list(to_insert.keys()):
            #while expr_i<len(prob_exprs) and i+1==prob_exprs[expr_i].line:
                #to_paste = generate_sym_code(prob_exprs[expr_i])
                expr_i += 1
                ### MAJOR CHANGE: Currently we are not injecting intrumentation for branching conditions ###
                # copy_main = copy_main + to_insert[i+1]
        else: # Instead of not copying main, copy it with comments
            copy_main = copy_main + '//' + line

    return copy_main

def generate_main_aux(orig_fl, node, prob_exprs):
    global g_sym_var_count
    to_insert = {}
    for e in prob_exprs:
        param1 = ''
        if e[2].endswith('*'):
            datatype = e[2][:-1].strip()
            param1 = '%s'%e[1]
        else:
            datatype = e[2].strip()
            param1 = '&%s'%e[1]
        g_sym_var_count += 1
        to_insert[e[0]] = code_str
    main_node = find_func_node(node, 'main')
    if main_node:
        main_start, main_end = main_node.extent.start.line, main_node.extent.end.line
    else:
        main_start, main_end = -1, -2
    copy_main = ''
    expr_i = 0
    orig_fl.seek(0)
    for i, line in enumerate(orig_fl):
        if i+1 in range(main_start, main_end+1):
            if 'main(' in line.strip() or 'main (' in line.strip():
                line = line.replace('main', 'main_aux')
            copy_main = copy_main + line
            # copy_fl.write(line)
            if i+1 in list(to_insert.keys()):
            #while expr_i<len(prob_exprs) and i+1==prob_exprs[expr_i].line:
                # to_paste = generate_sym_code(prob_exprs[expr_i])
                expr_i += 1
                ### MAJOR CHANGE: Currently we are not injecting intrumentation for branching conditions ###
                # copy_main = copy_main + to_insert[i+1]

    return copy_main
    pass

def check_line_for_params(node, f):
    fl_name = f.name
    f = open(fl_name, 'r')
    line_n = node.location.line
    i = 0
    while True:
        line = f.readline()
        if not line: 
            break
        i += 1
        if i+1==line_n:
            break

    next_line = f.readline()
    if '(' not in line:
        line = next_line

    if '(' not in line:
        return []

    param_start = line.split('(')[1]
    param_split = param_start.split(',')
    
    params = []
    for p in param_split:
        p = p.strip()
        p = p.strip('() ')
        if ' ' not in p:
            continue
        tokens = p.split()
	datatype, var = p[-2:]
	if 'const' in tokens:
            datatype = 'const' + datatype
        if '*' in var:
            datatype = datatype + '*'
            var = var.strip('* ')
        params.append((datatype, var))

    return params

def generate_decl_code(node, f):
    global decl_vars
    decl_code = []

    ch = [c for c in node.get_children()]
    
    n_params = 0
    for c in ch:
        if c.kind==CursorKind.PARM_DECL:
            n_params += 1

    # What if you can't get parameter declarations? Maybe there are no params, or maybe CLANG couldn't get them
    if n_params==0:
        params = check_line_for_params(node, f)

        if len(params)!=0:
            decl_line = ''
            for datatype, var in params:
                if var not in decl_vars:
                    decl_line = datatype + ' ' + var + ';\n'
                    #decl_vars.append(var)
                if datatype.endswith('*'):
                    if datatype[:4].lower()=='char':
                        alloc_line = var + ' = malloc(sizeof(' + datatype[:-1].strip() + ')*100);\n'
                    else:
                        alloc_line = var + ' = malloc(sizeof(' + datatype[:-1].strip() + '));\n'
                    decl_line = decl_line + alloc_line
                decl_code.append(decl_line)

    for c in ch:
        decl_line = ''
        if c.kind==CursorKind.PARM_DECL:
            #The part commented below is only needed if generating unit tests in the same C file
            #if c.spelling not in decl_vars:
            decl_line = c.type.spelling + ' ' + c.spelling + ';\n'
            decl_vars.append(c.spelling)
            if c.type.spelling.endswith('*'):
                if c.type.spelling[:4].lower()=='char':
                    alloc_line = c.spelling + ' = malloc(sizeof(' + c.type.spelling[:-1].strip() + ')*100);\n'
                else:
                    alloc_line = c.spelling + ' = malloc(sizeof(' + c.type.spelling[:-1].strip() + '));\n'
                decl_line = decl_line + alloc_line
            decl_code.append(decl_line)

    return decl_code

def generate_sym_params(node, f):
    instr_code = []
    ch = [c for c in node.get_children()]
    n_params = 0
    for c in ch:
        if c.kind==CursorKind.PARM_DECL:
            n_params += 1

    if n_params==0:
        params = check_line_for_params(node, f)

        if len(params)!=0:
            for datatype, var in params:
                instr_code.append(generate_sym_code(Expr(node.location, var, datatype)))

    for c in ch:
         if c.kind==CursorKind.PARM_DECL:
             instr_code.append(generate_sym_code(Expr(c.location, c.spelling, c.type.spelling)))

    return instr_code

def generate_main_code(inj_code, f): # previously - node, decl_code, inj_code
    main_blocks = {}
    main_func = 'int main(int argc, char * argv[]) {\n'
    
    for inj in inj_code:
        cur_main_block = main_func
        node, decl_code, instr_code = inj
        for d in decl_code:
            cur_main_block = cur_main_block + d
        
        for i in instr_code:
            cur_main_block = cur_main_block + i

        if node.spelling=='main':
            main_blocks['main'] = ' '
            #node_spelling = 'main_aux'
            #cur_main_block = cur_main_block + 'return main_aux(argc, argv);\n}'
            continue
        else:
            node_spelling = node.spelling
        cur_main_block = cur_main_block + node_spelling + '('
        ch = [c for c in node.get_children()]
        
        # For cases when CLANG can't read the function params
        n_params = 0
        for c in ch:
            if c.kind==CursorKind.PARM_DECL:
                n_params += 1

        if n_params==0:
            params = check_line_for_params(node, f)

            for i, (datatype, var) in enumerate(params):
                cur_main_block = cur_main_block + var
                if len(params)>i+1:
                    cur_main_block = cur_main_block + ','

        for i, c in enumerate(ch):
            if c.kind==CursorKind.PARM_DECL:
                cur_main_block = cur_main_block + c.spelling
                if len(ch)>(i+1) and ch[i+1].kind==CursorKind.PARM_DECL:
                    cur_main_block = cur_main_block + ', '

        cur_main_block = cur_main_block + ');\n\n'
    
        cur_main_block = cur_main_block + 'return 0;\n'
        cur_main_block = cur_main_block + '}'

        main_blocks[node.spelling] = (cur_main_block)

    return main_blocks


def get_func_nodes(node):
    global func_nodes
    
    # if node.spelling!='main' and node.kind==CursorKind.FUNCTION_DECL and str(node.location.file).endswith('.c'): # Don't look at the header files
    if node.kind==CursorKind.FUNCTION_DECL and str(node.location.file).endswith('.c'): # Don't look at the header files
        ch = [c for c in node.get_children()]
        for c in ch:
            if c.kind==CursorKind.COMPOUND_STMT:
                func_nodes.append(node)
    ch = [c for c in node.get_children()]
    for c in ch:
            get_func_nodes(c)

def main():

    global opts
    global g_sym_var_count
    global func_nodes
    global decl_vars

    decl_vars = []
    func_nodes = []

    inj_code = []
    func_names = []
    prob_branch = []
    prob_exprs = []

    parser = OptionParser("usage: %prog -f {source filename} [-n {func_to_test}] [-a {test all functions}]")
    parser.add_option('-f', '--file', action='store', type='string', dest='filename', default='None', help='Source file name')
    parser.add_option('-a', '--all', action='store_true', dest='all_funcs', default='False', help='Analyse all functions in the source file')
    parser.add_option('-n', '--name', action='store', type='string', dest='func_name', default='None', help='Name of the function to be analysed')

    (opts, args) = parser.parse_args()


    # pprint(('diags', map(get_diag_info, tu.diagnostics)))

    # Transform using a command line flag
    all_funcs = opts.all_funcs
    src_fl_name = opts.filename
    func_name = opts.func_name

    if not src_fl_name.endswith('.c'):
        print('The input file does not seem to be a C source.\n"--help" for usage\nExiting.')
        sys.exit()

    index = Index.create()
    tu = index.parse(src_fl_name)
    if not tu:
        parser.error("unable to load input")
    

    # Very important: Which function to unit test?
    if all_funcs==True:
        print('analysing all functions in source file: ' + src_fl_name)
        get_func_nodes(tu.cursor)
        
        for f in func_nodes:
            func_names.append(f.spelling)

    else:
        if func_name==None:
            print('Supply function name using flag "-n"\nOr use "-a" to analyse all functions')
            sys.exit(-1)

        print('analysing ' + func_name + ' in source file: ' + src_fl_name)
        func_names = [func_name]

    orig_fl = open(src_fl_name, 'r')
    for f in func_names:
        func_node = find_func_node(tu.cursor, f)
        if not func_node:
            print('No function found with the name: ' + f+ '\nSomething went wrong')
            continue
            #sys.exit(-1)
        
        decl_code = generate_decl_code(func_node, orig_fl)
        instr_code = generate_sym_params(func_node, orig_fl)

        inj_code.append((func_node, decl_code, instr_code))
        prob_branch_res, prob_expr = analyze(src_fl_name, f)
        prob_branch.extend(prob_branch_res)
        prob_exprs.extend(prob_expr)
    
    modified_prob_exprs = []
    for pb in prob_branch:
        if ":" not in pb:
            print("Found some problem in branch. Trying to move on\n")
            continue
        line, symb, st  = pb.split(':')[:3]
        line = int(line.strip())
        symb = symb.strip()
        # Find datatype of symb
        datatype = ''
        for ex in prob_exprs:
            if ex.iden==symb:
                datatype = ex.datatype
        if datatype=='':
            print('Something went wrong.\nExiting.')
            sys.exit(-1)

        modified_prob_exprs.append((line, symb, datatype))

    main_funcs = generate_main_code(inj_code, orig_fl)
    orig_fl.close()
    
    orig_fl = open(src_fl_name, 'r')
    all_minus_main = copy_all_minus_main(orig_fl, tu.cursor, modified_prob_exprs)
    
    '''
    if 'main' in func_names: # Analyzing main function
        main_aux = generate_main_aux(orig_fl, tu.cursor, modified_prob_exprs)
    '''
    # Finally write all unit tests inside a folder
    if not os.path.isdir(src_fl_name[:-2]+'_units'):
        os.system('mkdir '+src_fl_name[:-2]+'_units')

    for unit_i, func_name in enumerate(main_funcs.keys()):
        if func_name=='main':
            os.system('cp ' + src_fl_name + ' ' + src_fl_name[:-2]+ '_units/' + os.path.basename(src_fl_name)[:-2]+'_'+func_name+'.c.units')
        else:
            instr_fl = open(src_fl_name[:-2]+'_units/' + os.path.basename(src_fl_name)[:-2]+'_'+func_name+'.c.units', 'w')
            instr_fl.write(all_minus_main) #TODO: send prob_branch and prob_exprs to instrument code in the functions

            instr_fl.write(main_funcs[func_name])
            instr_fl.close()
        callee_fl = open(src_fl_name[:-2]+'_units/' + os.path.basename(src_fl_name)[:-2]+'_'+func_name+'.c.callee', 'w')
        callee_list = get_callee_list(tu.cursor, func_name)
        for c in callee_list:
            if not c=='':
                callee_fl.write(c+'\n')

        callee_fl.close()
    
    hints_fl = open(src_fl_name+'.hints', 'w')
    if len(prob_branch)>0:
        print('Some assignments may benefit from symbolic return values -')
        print('Recorded these line numbers in %s.hints'%(src_fl_name))
        hints_fl.write('line# : var : statement\n')
        for b in prob_branch:
            hints_fl.write(b+'\n')
        # inject_symbolic_code(src_fl_name[:-2]+'.c.units', prob_exprs)
        


if __name__ == '__main__':
    main()

