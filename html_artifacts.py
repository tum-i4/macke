import sys, os, glob
import re
from optparse import OptionParser, OptionGroup
import subprocess

HTML_SRC = 'html1'

if __name__=='__main__':
    # parse arguments
    parser = OptionParser("usage: %prog -d {directory containing source files}")
    parser.add_option('-d', '--dir', action='store', type='string', dest='dir', help='Source file directory path')

    (opts, args) = parser.parse_args()
    dir_name = opts.dir

    if not dir_name.endswith('/'):
        dir_name += '/'

    if not os.path.isdir(dir_name + HTML_SRC):
        os.system('mkdir ' + dir_name + HTML_SRC)

    for d in glob.glob(dir_name + '*_units/*_*.c.units'):
        re_pattern = dir_name + '(.*)_units/(.*)_(.*).c.units'
        re_match = re.search(re_pattern, d)
        re_pattern_actual = dir_name + '(.*)_units/(.*?)_(.*).c.units'
        re_match_actual = re.search(re_pattern_actual, d)
        func_name_actual = re_match_actual.group(3)
        func_name = re_match.group(3)
        main_name = re_match.group(1)

        ptr_errs = glob.glob(dir_name + main_name + '_units/' + main_name + '_' + func_name + '/*.ptr.err')
        ptr_errs_actual = glob.glob(dir_name + main_name + '_units/' + main_name + '_' + func_name_actual + '/*.ptr.err')
        if (len(ptr_errs)<1 and len(ptr_errs_actual)<1) or (not os.path.isdir(dir_name + main_name + '_units/' + main_name + '_' + func_name + '/') and not os.path.isdir(dir_name + main_name + '_units/' + main_name + '_' + func_name_actual + '/')):
            print 'Generating alternative HTML for ' + func_name
            parent_test_case = open(dir_name + HTML_SRC + '/' + func_name_actual + '.html', 'w')
            parent_test_case.write('<html>Nothing found for %s.<p/>Maybe the function does not contain any known vulnerabilities, but it is close enough to a function that does. Consider sanitizing the input to functions being called by %s<p/><br/></html>'%(func_name_actual, func_name_actual))
            parent_test_case.close()
            continue

        print 'Generating HTML for ' + func_name_actual
        parent_test_case = open(dir_name + HTML_SRC + '/' + func_name_actual + '.html', 'w')
        parent_test_case.write('<html>Following test case(s) in %s resulted in memory out-of-bounds errors. Click for more details<p/><br/>'%(func_name_actual))
        parent_test_case.close()

    for f in glob.glob(dir_name + '*_units/*/test*.ptr.err'):
        re_pattern = dir_name + '(.*)_units/(.*)_(.*)/(.*).ptr.err'
        re_match = re.search(re_pattern, f)
        func_name = re_match.group(3)
        test_case = re_match.group(4)

        test_case_pagename_relative = '%s_%s.html'%(func_name, test_case)
        test_case_page = open('%s%s/%s_%s.html'%(dir_name, HTML_SRC, func_name, test_case), 'w')

        test_case_page.write('<html>\n')

        out = os.popen('cat ' + f).read()
        out = out.replace('\n', '\n<p/>')

        '''
        proc = subprocess.Popen(['cat', f], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        '''

        test_case_page.write(out)
        test_case_page.write('<p/><br/>')

        '''
        proc = subprocess.Popen(['ktest-tool', f[:-7]+'ktest'], stdout=subprocess.PIPE, shell=True)
        (out, err) = proc.communicate()
        '''

        out = os.popen('ktest-tool ' + f[:-7]+'ktest').read()
        out = out.replace('\n', '\n<p/>')

        test_case_page.write(out)
        test_case_page.write('</html>')
        test_case_page.close()

        parent_test_case = open(dir_name + HTML_SRC + '/' + func_name + '.html', 'a')
        parent_test_case.write('<a href="%s">%s</a><p/>'%(test_case_pagename_relative, test_case))
        parent_test_case.close()

