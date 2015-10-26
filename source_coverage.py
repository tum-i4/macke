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

def generate_simplified_run_istats_targeted(src_dir):
    files_lines_cov = {}
    files_lines_seen = {}

    if not src_dir.endswith('/'):
        src_dir = src_dir+'/'

    # Read all run.istats
    for r in glob.glob(src_dir + '*_units/*_targeted_*/run.istats'):
        istats = open(r, 'r')
        line = ' '
        print 'Reading: ' + r
        # Read the file line by line#
        while line!='':
            # Read and discard till a line found in a C file from current source directory
            while line!='':
                if line.strip().startswith('fl=') and src_dir in line:
                    break
                line = istats.readline()

            if line=='':
                print 'No source line found in: ' + r
                continue

            full_filename = line.strip().split('=')[1]
            file_key = os.path.split(full_filename)[1]

            print 'Seen file: ' + file_key
            temp_seen = []
            temp_cov = []

            # Read till the next source file is seen
            while line!='':
                line = istats.readline()
                if line.strip().startswith('fl='):
                    break
                tokens = line.strip().split()
                if not tokens[0].isdigit() or not len(tokens)==15:
                    continue
                src_line = int(tokens[1])
                cov_i = int(tokens[2])

                if src_line not in temp_seen:
                    temp_seen.append(src_line)
                if cov_i>0 and src_line not in temp_cov:
                    temp_cov.append(src_line)

            # If any lines were seen at all
            if temp_seen!=[]:
                # Add source file and lines covered to the dictionaries
                if file_key in files_lines_cov:
                    files_lines_cov[file_key].extend(temp_cov)
                else:
                    files_lines_cov[file_key] = temp_cov

                # Same for seen lines
                if file_key in files_lines_seen:
                    files_lines_seen[file_key].extend(temp_seen)
                else:
                    files_lines_seen[file_key] = temp_seen

    # Remove duplicates
    for k in files_lines_cov.keys():
        files_lines_cov[k] = set(files_lines_cov[k])
        files_lines_cov[k] = [e for e in files_lines_cov[k]]

    for k in files_lines_seen.keys():
        files_lines_seen[k] = set(files_lines_seen[k])
        files_lines_seen[k] = [e for e in files_lines_seen[k]]
    
    return files_lines_cov, files_lines_seen

def generate_simplified_run_istats(src_dir):
    files_lines_cov = {}
    files_lines_seen = {}

    if not src_dir.endswith('/'):
        src_dir = src_dir+'/'

    # Read all run.istats
    for r in glob.glob(src_dir + '*_units/*_*/run.istats'):
        istats = open(r, 'r')
        line = ' '
        print 'Reading: ' + r
        # Read the file line by line#
        while line!='':
            # Read and discard till a line found in a C file from current source directory
            while line!='':
                if line.strip().startswith('fl=') and src_dir in line:
                    break
                line = istats.readline()

            if line=='':
                print 'No source line found in: ' + r
                continue

            full_filename = line.strip().split('=')[1]
            file_key = os.path.split(full_filename)[1]

            print 'Seen file: ' + file_key
            temp_seen = []
            temp_cov = []

            # Read till the next source file is seen
            while line!='':
                line = istats.readline()
                if line.strip().startswith('fl='):
                    break
                tokens = line.strip().split()
                if not tokens[0].isdigit() or not len(tokens)==15:
                    continue
                src_line = int(tokens[1])
                cov_i = int(tokens[2])

                if src_line not in temp_seen:
                    temp_seen.append(src_line)
                if cov_i>0 and src_line not in temp_cov:
                    temp_cov.append(src_line)

            # If any lines were seen at all
            if temp_seen!=[]:
                # Add source file and lines covered to the dictionaries
                if file_key in files_lines_cov:
                    files_lines_cov[file_key].extend(temp_cov)
                else:
                    files_lines_cov[file_key] = temp_cov

                # Same for seen lines
                if file_key in files_lines_seen:
                    files_lines_seen[file_key].extend(temp_seen)
                else:
                    files_lines_seen[file_key] = temp_seen

    # Remove duplicates
    for k in files_lines_cov.keys():
        files_lines_cov[k] = set(files_lines_cov[k])
        files_lines_cov[k] = [e for e in files_lines_cov[k]]

    for k in files_lines_seen.keys():
        files_lines_seen[k] = set(files_lines_seen[k])
        files_lines_seen[k] = [e for e in files_lines_seen[k]]
    
    return files_lines_cov, files_lines_seen

                
def source_coverage(c_filename):
    src_dir = os.path.dirname(c_filename)
    main_name = os.path.splitext(os.path.basename(c_filename))[0]

    cov_lines = [] 
    seen_lines = []

    if not src_dir.endswith('/'):
        src_dir = src_dir + '/'

    for istats_file in glob.glob(src_dir + main_name + '_units/*/run.istats'):
    #for istats_file in glob.glob(src_dir + '*_units/*/run.istats'):
        print 'reading ' + istats_file
        temp_cov_lines, temp_seen_lines = get_source_coverage(c_filename, istats_file, cov_lines, seen_lines)
        cov_lines.extend(temp_cov_lines)
        seen_lines.extend(temp_seen_lines)

    cov_lines = set(cov_lines)
    seen_lines = set(seen_lines)
    cov_lines = [c for c in cov_lines]
    seen_lines = [s for s in seen_lines ]
    return cov_lines, seen_lines

def project_coverage(src_dir):
    cov = []
    seen = []
    for c in glob.glob(src_dir+'*.c'):
        temp_cov, temp_seen = source_coverage(c)
        cov.extend(temp_cov)
        seen.extend(temp_seen)

    return cov, seen

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
