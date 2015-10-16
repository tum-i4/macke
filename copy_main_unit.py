import glob, os
import sys

if __name__=='__main__':
    dir_name = sys.argv[1]
    print dir_name
    for f in glob.glob(dir_name+'/*.c'):
        print 'Creating unit test functions for ' + f
        c_file = open(f, 'r')
        orig_unit = open(f+'.units', 'r')
        mod_unit = open(f+'.units.mod', 'w')

        mod_unit.write('#include <klee/klee.h> //Generated code - Macke framework\n')
        for line in c_file:
            mod_unit.write(line)

        while True:
            line = orig_unit.readline()
            if not line:
                break
            if line.startswith('int main'):
                break

        mod_unit.write(line)
        while True:
            line = orig_unit.readline()
            if not line:
                break
            mod_unit.write(line)

        mod_unit.close()
        orig_unit.close()
        c_file.close()

