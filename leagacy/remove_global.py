import glob, os, sys

lower_types = ['char', 'void', 'boolean', 'int']
convert_to = ['char', 'void', 'bool', 'int']

def type_convert_lower(st):
    toks = st.split()
    st_cp = ''
    for i, t in enumerate(toks):
        if t.lower() in lower_types:
            toks[i] = t.lower()
            #ind = lower_types.index(t.lower())
            #toks[i] = convert_to[ind]
        st_cp = st_cp + ' ' + toks[i]
    st_cp = st_cp + '\n'

    return st_cp

def str_without_qual(st):
    toks = st.split()
    toks = toks[1:]
    st_cp = ''
    for t in toks:
        st_cp = st_cp + t + ' '
    st_cp = st_cp + '\n'

    return st_cp

if __name__=='__main__':
    dir_name = sys.argv[1]
    print('copying files in ' + dir_name)

    for src in glob.glob(dir_name+'/*.c'):
        fl = open(src, 'r')
        fl_cp = open(src+'.copy', 'w')

        # fl_cp.write('#include <stdbool.h>\n')
        for line in fl:
            toks = line.split()
            if len(toks)>1 and (toks[0]=='GLOBAL' or toks[0]=='LOCAL'):
                line_cp = str_without_qual(line)
            else:
                line_cp = line
            # line_cp = type_convert_lower(line_cp)

            fl_cp.write(line_cp)
        fl_cp.close()


