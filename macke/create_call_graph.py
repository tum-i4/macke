import glob, os, sys
import pydot 
import re
from optparse import OptionParser, OptionGroup
from clang.cindex import Index, CursorKind
from .callee import get_callee_list

COLOR_RANGE = ['#ffffff', '#ffe5e5', '#ff9999', '#ff4c4c', '#ff0000']
SEVERITY_RANGES = {(0, 1): 0, 
        (1, 10): 1, 
        (10, 20): 2, 
        (20, 40): 3, 
        (40, 10000): 4}

LONG_CHAIN = 5
KNOWN_INTERFACE = 4
PROXIMITY_TO_MAIN = 3
TOTAL_ERRORS = 3
HIGH_OCCURENCE = 4
ERROR_EXISTS = 3
HTML_SRC = 'html4/'

known_interfaces = ['bzip2Main', 'bzip2recoverMain']
nodes = []
pydot_nodes = {}
edges = {}
pydot_edges = {}

not_leaf = []

dir_name = ''

bug_chains = []
outliers = []

def temp_hack(dir_name, main_file, main_file_bkp):
    main_file_name = main_file[:-2]
    if os.path.exists(dir_name + '%s_units/%s_main.c.callee'%(main_file_name, main_file_name)):
        return
    
    os.system('mv %s%s %s%s.new'%(dir_name, main_file, dir_name, main_file))
    os.system('mv %s%s %s%s'%(dir_name, main_file_bkp, dir_name, main_file))

    index = Index.create()
    tu = index.parse(dir_name + main_file)

    callee_list = get_callee_list(tu.cursor, 'main')

    callee_file = open(dir_name + '%s_units/%s_%sMain.c.callee'%(main_file_name, main_file_name, main_file_name), 'w+')
    for c in callee_list:
        callee_file.write(c + '\n')
    callee_file.close()

    os.system('mv %s%s %s%s'%(dir_name, main_file, dir_name, main_file_bkp))
    os.system('mv %s%s.new %s%s'%(dir_name, main_file, dir_name, main_file))

def shortest_dist(source, dest, how_deep):
    if how_deep>=10:
        return 10
    min_dist = 10000
    if source not in list(edges.keys()):
        return min_dist
    if dest in edges[source]:
        return 1
    for s in edges[source]:
        cur_shortest = shortest_dist(s, dest, how_deep+1) + 1
        if cur_shortest<min_dist:
            min_dist = cur_shortest
    return min_dist

def distance_to_interface(unit_name):
    min_interface_dist = 100000
    for i in known_interfaces:
        interface_dist = shortest_dist(i, unit_name, 0)
        if interface_dist<min_interface_dist:
            min_interface_dist = interface_dist

    return min_interface_dist

def get_node_decoration(filename, unit_name):
    severity = 0
    url = ''
    test_dir = dir_name + filename + '_units/' + filename + '_' + unit_name + '/'
    if not os.path.isdir(test_dir):
        return 'white', severity, url

    errs = glob.glob(test_dir + '*.ptr.err')
    if not errs==[]:
        dist_to_interface = distance_to_interface(unit_name)
        if dist_to_interface>=10:
            dist_to_interface = 9

        severity += PROXIMITY_TO_MAIN*(10-dist_to_interface)

        # How many errors in the function?
        severity += TOTAL_ERRORS*len(errs)

        # check if exists in chains
        for c in bug_chains:
            if unit_name in c:
                severity += len(c)*LONG_CHAIN

        # check if in a known interface
        if unit_name in known_interfaces:
            severity += KNOWN_INTERFACE

        # check if it occurs too many times
        if unit_name in outliers:
            severity += HIGH_OCCURENCE

        unit_name_mod = unit_name
        if '_' in unit_name:
            unit_name_mod = unit_name.split('_')[-1]

        url = unit_name_mod + '.html'

    for s in list(SEVERITY_RANGES.keys()):
        if severity in range(s[0], s[1]):
            severity_index = SEVERITY_RANGES[s]

    return COLOR_RANGE[severity_index], severity, url

def create_nodes_and_edges():

    for f in glob.glob(dir_name + '*_units/*.c.callee'):
        pattern = dir_name + '(.*)_units/(.*?)_(.*).c.callee'
        re_match = re.search(pattern, f)

        nodes.append(re_match.group(3))
        
        callee_file = open(f, 'r')
        node_edges = []
        for line in callee_file:
            node_edges.append(line.strip())

        edges[re_match.group(3)] = node_edges
    
def create_pydot_nodes():
    colors = {}
    tooltips = {}
    urls = {}
    for f in glob.glob(dir_name + '*_units/*.c.callee'):
        pattern = dir_name + '(.*)_units/(.*?)_(.*).c.callee'
        re_match = re.search(pattern, f)
        colors[re_match.group(3)], tooltips[re_match.group(3)], urls[re_match.group(3)] = get_node_decoration(re_match.group(1), re_match.group(3).split('_')[-1])
    
    for n in nodes:
        if urls[n]!='':
            pydot_nodes[n] = pydot.Node(n, style='filled', fillcolor=colors[n], tooltip=tooltips[n], URL=urls[n])
        else:
            pydot_nodes[n] = pydot.Node(n, style='filled', fillcolor=colors[n], tooltip=tooltips[n])

def create_pydot_edges():
    for n in list(edges.keys()):
        node_ends = edges[n]

        for e in node_ends:
            if e not in nodes:
                continue
            if n=='main':
                print(e)
            pydot_edges[(pydot_nodes[n], pydot_nodes[e])] = pydot.Edge(pydot_nodes[n], pydot_nodes[e])

def read_composition_file():
    composition_file = open(dir_name + 'composition.test')

    line = composition_file.readline()
    while not line=='':
        current_chain = []
        current_chain.append(line.strip().split()[0])
        line = composition_file.readline()
        tokens = line.split(',')
        for t in tokens:
            t = t.strip(" ,'()[]\n")
            if not t.endswith('.c'):
                if t in current_chain: # Probably an outlier
                    outliers.append(t)
                else:
                    current_chain.append(t)
        bug_chains.append(current_chain)
        line = composition_file.readline() #Empty line ideally
        line = composition_file.readline()

if __name__=='__main__':
    nodes = []
    edges = {}
    pydot_nodes = {}
    pydot_edges = {}

    parser = OptionParser("usage: %prog -d {directory containing source files}")
    parser.add_option('-d', '--dir', action='store', type='string', dest='dir', help='Source file directory path')
    parser.add_option('-m', '--main', action='store', type='string', dest='main_file', help='Source file containing main function')
    parser.add_option('-b', '--main-backup', action='store', type='string', dest='main_file_bkp', help='Main file backup')

    (opts, args) = parser.parse_args()
    dir_name = opts.dir
    main_file = opts.main_file
    main_file_bkp = opts.main_file_bkp

    if not dir_name[-1]=='/':
        dir_name += '/'

    if not os.path.isdir(dir_name):
        print('There does not seem to be a directory with that name: ' + dir_name)
        sys.exit(-1)

    temp_hack(dir_name, main_file, main_file_bkp)
    
    read_composition_file()
    graph = pydot.Dot(graph_type='digraph', splines='ortho')

    # Making all nodes and edges data structures (not the pydot structures)
    create_nodes_and_edges()
    
    # Making pydot nodes
    create_pydot_nodes()
    for n in nodes:
        graph.add_node(pydot_nodes[n])

    # Making pydot edges
    create_pydot_edges()

    for pe in list(pydot_edges.keys()):
        graph.add_edge(pydot_edges[pe])

    if not os.path.isdir(dir_name + HTML_SRC):
        os.system(dir_name + HTML_SRC)

    graph.write_svg(dir_name + HTML_SRC + 'call_graph.svg')
