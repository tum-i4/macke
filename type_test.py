#!/usr/bin/env python
""" Usage: call with <filename> <typename>
"""

import sys
import clang.cindex
import asciitree

def node_children(node):
    return [c for c in node.get_children()]
    # return (c for c in node.get_children() if c.location.file.name == sys.argv[1])

def print_node(node):
    text = node.spelling or node.displayname
    kind = str(node.kind) #[str(node.kind).index('.')+1:]
    return '{} {}'.format(kind, text)

def find_typerefs(node, typename):
    """ Find all references to the type named 'typename'
    """
    if node.kind.is_reference():
        ref_node = clang.cindex.Cursor_ref(node)
        if ref_node.spelling == typename:
            print 'Found %s [line=%s, col=%s]' % (
                typename, node.location.line, node.location.column)
    # Recurse for children of this node
    for c in node.get_children():
        find_typerefs(c, typename)

clang.cindex.Config.set_library_file('/usr/lib/x86_64-linux-gnu/libclang.so')
index = clang.cindex.Index.create()
tu = index.parse(sys.argv[1])
print 'Translation unit:', tu.spelling
print asciitree.draw_tree(tu.cursor, node_children, print_node)
find_typerefs(tu.cursor, sys.argv[2])
