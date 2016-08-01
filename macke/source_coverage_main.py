from source_coverage import get_source_coverage
import os, glob
from optparse import OptionParser, OptionGroup

if __name__=='__main__':
    parser = OptionParser('Usage: %prog -d {name of the source directory}')
    parser.add_option('-d', '--dir', action='store', type='string', dest='dir', help='Source file directory path')

    (opts, args) = parser.parse_args()
    
    src_dir = opts.dir
    if not src_dir.endswith('/'):
        src_dir += '/'

    cov_lines = []
    seen_lines = []

    for istats in glob.glob(src_dir + '*/run.istats'):
        for c_filename in glob.glob(src_dir+'*.c'):
            print c_filename
	    cov_lines, seen_lines = get_source_coverage(c_filename, istats, cov_lines, seen_lines)

    print 'Covered: ' + str(len(cov_lines))
    print 'coverage: ' + str(float(len(cov_lines))/float(len(seen_lines)))
