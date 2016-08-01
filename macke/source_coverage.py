import os, glob
from optparse import OptionParser, OptionGroup

def get_source_coverage(c_filename, istats_path, cov_lines, seen_lines):
    istats = open(istats_path, 'r')
    main_filename = os.path.basename(c_filename)
    line = ''
    # Find starting line of the source file
    for i, line in enumerate(istats):
        if line.strip().startswith('fl=') and main_filename in line:
            break

    if line=='':
        print 'Could not find source filename in the run.istats file: ' + main_filename
        return [], []

    fl_start = i

    for line in istats:
        # Read only the lines that have the pattern
        if line.startswith('fl='):
            break
        tokens = line.strip().split()
        if not tokens[0].isdigit() or not len(tokens)==15:
            continue
        src_line = int(tokens[1])
        cov_i = int(tokens[2])
        
        if src_line not in seen_lines:
            seen_lines.append(src_line)
        if cov_i>0 and src_line not in cov_lines:
            cov_lines.append(src_line)

    return cov_lines, seen_lines

def source_coverage(c_filename):
    src_dir = os.path.dirname(c_filename)
    main_name = os.path.splitext(os.path.basename(c_filename))[0]

    cov_lines = [] 
    seen_lines = []

    if not src_dir.endswith('/'):
        src_dir = src_dir + '/'

    for istats_file in glob.glob(src_dir + main_name + '_units/*/run.istats'):
        print 'reading ' + istats_file
        cov_lines, seen_lines = get_source_coverage(c_filename, istats_file, cov_lines, seen_lines)

    return cov_lines, seen_lines

if __name__=='__main__':
    parser = OptionParser('Usage: %prog -d {name of the source directory}')
    parser.add_option('-d', '--dir', action='store', type='string', dest='dir', help='Source file directory path')

    (opts, args) = parser.parse_args()
    
    src_dir = opts.dir

    if not src_dir.endswith('/'):
        src_dir = src_dir + '/'
    
    tot_cov = 0
    tot_seen = 0
    
    coverage_file = open(src_dir+'src.coverage', 'w+')
    for f in glob.glob(src_dir + '/*.c'):
        cov, seen = source_coverage(f)
        tot_cov += len(cov)
        tot_seen += len(seen)
    
    coverage_file.write(str(float(tot_cov)/tot_seen))
