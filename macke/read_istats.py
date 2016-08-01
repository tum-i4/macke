import sys, os

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__=='__main__':
    # folders = ['blocksort', 'compress', 'crctable', 'decompress', 'huffman', 'randtable']
    folders = ['klee-last']
    dir = '/home/ognawala/stonesoup/stonesoup-c-mc/bzip2/'
    funcs = {}
    
    for fold in folders:
        istats = open(dir+fold+'/run.istats', 'r')
        
        line = istats.readline()
        while line!='': # Read the entire file
            if line.startswith('fl=') and (dir in line): # Found a line with a file location
                line = istats.readline()
                while ('=' not in line) and line!='':
                    line = istats.readline()
                if line=='':
                    continue
                toks = line.split('=')
                while toks[0]=='fn': # Read all function in a file
                    func_name = toks[1].strip()
                    line = istats.readline()
                    toks = line.split()
                    while line!='' and is_number(toks[0]): # Read all the lines in a function
                        if func_name not in funcs.keys():
                            funcs[func_name] = 0
                        funcs[func_name] += int(toks[2]) # Incremention covered-instruction count for the function
                        line = istats.readline()
                        toks = line.split()
                    if line!='':
                        toks = line.split('=')
                    else:
                        toks = ['']
                continue # Next line already read. Don't read again
            line = istats.readline()

    # Funcs should be full by now

    print funcs

