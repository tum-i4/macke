from clang.cindex import Index, CursorKind
from branch_analyzer import analyze
import sys, os
from generate_unit import find_func_node

def get_callee_list_rec(node, callee_list):
    ch = [c for c in node.get_children()]
    if node.kind==CursorKind.CALL_EXPR and str(node.location.file).endswith('.c'):
        callee_list.append(node.spelling)

    for c in ch:
        c_callee = get_callee_list_rec(c, [])
        if len(c_callee)>0:
            callee_list.extend(c_callee)
    
    return callee_list

def get_callee_list(node, func_name):
    func_node = find_func_node(node, func_name)
    if not func_node:
        print 'Function not found'
        return None

    ch = [c for c in func_node.get_children()]

    callee_list = get_callee_list_rec(func_node, [])
    callee_list = set(callee_list)
    return callee_list

if __name__=='__main__':
    filename = sys.argv[1]
    func_name = sys.argv[2]

    index = Index.create()
    tu = index.parse(filename)

    print get_callee_list(tu.cursor, func_name)

