from clang.cindex import Index, CursorKind
from pprint import pprint
import sys

from optparse import OptionParser, OptionGroup
import clang.cindex

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

class Symbol:
    def __init__(self, iden, location):
        self.iden = iden
        self.line = location.line

    def __str__(self):
        return self.iden

    def __repr__(self):
        return self.iden
    
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if self.iden==other.iden:
            return True
        else:
            return False

    def __lt__(self, other):
        if self.line<other.line:
            return True
        else:
            return False

prob_exprs = []
prob_lines = []
sym_table = {}
call_table = {}
g_sym_var_count = 0

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

def get_cursor_id(cursor, cursor_list = []):
    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i,c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1

def get_conditional_statement_info(node):
    ch = [get_conditional_statement_info(c) for c in node.get_children()]
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
         'children' : ch }

def proc_member_ref_expr(node):
    datatype = node.type.spelling
    mem = node.displayname
    unexposed_expr = [c for c in node.get_children()][0]
    parent_struct = [c for c in unexposed_expr.get_children()][0]
    struct_name = parent_struct.spelling
    if parent_struct.type.spelling.endswith('*'):
        connector = '->'
    else:
        connector = '.'
    res = Expr(parent_struct.location, struct_name+connector+mem, datatype)
    return res

def proc_array_subscript(underlying_expr):
    sub_expr = []

    while underlying_expr.kind!=CursorKind.UNEXPOSED_EXPR:
        ch = [c for c in underlying_expr.get_children()]
        if ch != []:
            underlying_expr = ch[0]
        else:
            return []

    underlying_expr = [c for c in underlying_expr.get_children()][0]
    if underlying_expr.kind==CursorKind.MEMBER_REF_EXPR: # Struct
        sub_expr.append(proc_member_ref_expr(underlying_expr))
    elif underlying_expr.kind==CursorKind.ARRAY_SUBSCRIPT_EXPR: # Special case: indexed array
        ind_array_underlying_expr = proc_array_subscript(underlying_expr)
        sub_expr.append(ind_array_underlying_expr)
    elif underlying_expr.kind==CursorKind.DECL_REF_EXPR: # Normal variable
        res = Expr(underlying_expr.location, underlying_expr.spelling, underlying_expr.type.spelling)
        sub_expr.append(res)
    
    return sub_expr

# TODO: change to return only name and type. Line number to be added by the calling component
def lookup_unexposed_exprs(node):
    exprs = []
    if node.kind==CursorKind.UNEXPOSED_EXPR:
        underlying_expr = [c for c in node.get_children()][0]
        if underlying_expr.kind==CursorKind.MEMBER_REF_EXPR: # Struct
            exprs.append(proc_member_ref_expr(underlying_expr))
        elif underlying_expr.kind==CursorKind.ARRAY_SUBSCRIPT_EXPR: # Special case: indexed array
            ind_array_underlying_expr = proc_array_subscript(underlying_expr)
            exprs.append(ind_array_underlying_expr)
        elif underlying_expr.kind==CursorKind.DECL_REF_EXPR: # Normal variable
            res = Expr(underlying_expr.location, underlying_expr.spelling, underlying_expr.type.spelling)
            exprs.append(res)
        else: # Unknown underlying expression
            print("Unknown underlying expression too hard for me to solve at line no: " + str(underlying_expr.location.line))
        return exprs
    else: # Keep going deeper until expression is found
        ch = [c for c in node.get_children()]
        for c in ch:
            exprs.extend(lookup_unexposed_exprs(c))
        return exprs

def lookup_decl_ref_exprs(node):
    exprs = []
    if node.kind==CursorKind.DECL_REF_EXPR:
        expr = Expr(node.location, node.displayname, node.type.spelling)
	exprs = [expr]
    else:
        ch = [c for c in node.get_children()]
        for c in ch:
            exprs.extend(lookup_decl_ref_exprs(c))
    return exprs

def proc_if_statement(node, line_location):
    global prob_exprs
    ch = [c for c in node.get_children()]
    
    cond = ch[0]
    # TODO: Change the call below to add line numbers as line_to_insert
    decl_ref_exprs = lookup_decl_ref_exprs(cond)
    prob_exprs.extend(decl_ref_exprs)

# cond_info = get_conditional_statement_info(node)

def get_info(node):
    global prob_exprs
    global prob_lines

    ch = [c for c in node.get_children()]
    if node.kind==CursorKind.IF_STMT or node.kind==CursorKind.WHILE_STMT:
		proc_if_statement(node, node.location.line)
    for c in ch:
        get_info(c)
    '''
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
    '''

def generate_sym_code(expr):
    global g_sym_var_count
    code_str = ('klee_make_symbolic(&(%s), sizeof(%s), "sym_var_%i");\n')%(expr.iden, expr.datatype, g_sym_var_count)
    g_sym_var_count += 1
    return code_str

def inject_symbolic_code(orig_fl_name):
    global prob_exprs
    global sym_table
    expr_i = 0
    if not orig_fl_name.endswith('.c'):
        print('Original file does not seem to be a C source file\nExiting...')
        sys.exit(-1)
    orig_fl = open(orig_fl_name, 'r')
    instr_fl = open(orig_fl_name[:-2]+'_instr.c', 'w')
    
    instr_fl.write('#include <klee/klee.h>\n')
    for orig_i, line in enumerate(orig_fl):
        instr_fl.write(line)
        only_exprs = [e.iden for e in prob_exprs]
        if expr_i<len(prob_exprs):
            to_lookup = only_exprs[expr_i][:only_exprs[expr_i].find('->')] if '->' in only_exprs[expr_i] else only_exprs[expr_i]
        while expr_i<len(prob_exprs) and sym_table[to_lookup]==orig_i+1:
            to_paste = generate_sym_code(prob_exprs[expr_i])
            instr_fl.write(to_paste)
            expr_i += 1
            if expr_i<len(prob_exprs):
                to_lookup = only_exprs[expr_i][:only_exprs[expr_i].find('->')] if '->' in only_exprs[expr_i] else only_exprs[expr_i]

    instr_fl.close()

def get_sym_table(node):
    global sym_table
    # TODO: fix to include only declaration from the current file 
    if node.kind==CursorKind.VAR_DECL and str(node.location.file).endswith('.c'):
        sym_table[node.spelling] = node.location.line
    children = [get_sym_table(c) for c in node.get_children()]

def contains_variable(expr, iden):
    if '->' in iden:
        iden = iden[:iden.find('->')]
    if expr.spelling == iden:
        return True
    else:
        ch = [c for c in expr.get_children()]
        if ch==[]:
            return False
        else:
            for c in ch:
                if contains_variable(c, iden):
                    return True
    return False

def contains_any_function_call(expr):
    if expr.kind==CursorKind.CALL_EXPR:
        return True, expr.spelling
    else:
        ch = [c for c in expr.get_children()]
        if ch==[]:
            return False, None
        for c in ch:
            child_contains = contains_any_function_call(c)
            if child_contains[0]:
                return child_contains
    return False, None

def get_call_table(node, iden):
    global call_table
    
    if node.kind==CursorKind.BINARY_OPERATOR: # Probably an assignment statement
        ch = [c for c in node.get_children()]
        lhs = ch[0] # This is where the variable should ideally reside at
        rhs = ch[1] # This is where, if the variable is in lhs, a function call may reside at

        if contains_variable(lhs, iden):
            function_contains = contains_any_function_call(rhs)
            if function_contains[0]:
                call_table[iden] = rhs.location.line, function_contains[1]
    else:
        ch = [get_call_table(c, iden) for c in node.get_children()]

def find_func_node(node, func_name):
    if node.kind==CursorKind.FUNCTION_DECL and node.spelling==func_name and str(node.location.file).endswith('.c'):
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

def get_suspect_lines(fl_name, call_table):
    orig_fl = open(fl_name, 'r')
    suspect_lines = []
    for key in call_table.keys():
        orig_fl = open(fl_name, 'r')
        for i, line in enumerate(orig_fl):
            if i+1<call_table[key][0]:
                continue
            suspect_line = str(call_table[key][0]) + ' : ' + key + ' : ' + line.strip()
            suspect_lines.append(suspect_line)
            break
        orig_fl.close()

    return suspect_lines

def analyze(src_fl_name, unit_name):
	global prob_exprs
	global prob_lines
	global g_sym_var_count
	global sym_table
	global call_table

	index = Index.create()
	tu = index.parse(src_fl_name)
	if not tu:
		parser.error("unable to load input")

	# pprint(('diags', map(get_diag_info, tu.diagnostics)))
	prob_exprs = []
	g_sym_var_count = 0

	# Very important: Which function to unit test?
	# unit_name = 'main'
	func_node = find_func_node(tu.cursor, unit_name)

	if not func_node:
		print 'No function found with that name.\nExiting'
		sys.exit(-1)

	get_sym_table(func_node)
	get_info(func_node)
	prob_exprs = set(prob_exprs)

	prob_exprs = sorted(prob_exprs)
	orig_exprs = [e.iden for e in prob_exprs]

	# For all problematic elements, get call table
	for e in orig_exprs:
		get_call_table(func_node, e)

	# print call_table
	# inject_symbolic_code(args[0])
	return get_suspect_lines(src_fl_name, call_table), prob_exprs


def main():

    global opts
    global prob_exprs
    global prob_lines
    global g_sym_var_count
    global sym_table
    global call_table

    
    parser = OptionParser("usage: %prog [options] {filename} [clang-args*]")
    parser.add_option("", "--show-ids", dest="showIDs",
                      help="Compute cursor IDs (very slow)",
                      action="store_true", default=False)
    parser.add_option("", "--max-depth", dest="maxDepth",
                      help="Limit cursor expansion to depth N",
                      metavar="N", type=int, default=None)
    parser.disable_interspersed_args()
    (opts, args) = parser.parse_args()

    if len(args) != 2:
        parser.error('invalid number arguments')
    
    src_fl_name = args[0]
    unit_name = args[1]
    
    print analyze(src_fl_name, unit_name)[0]

if __name__ == '__main__':
    main()

