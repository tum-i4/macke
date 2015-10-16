import glob, os

if __name__=='__main__':
    coreutils_path = '/mnt/ext-hdd/coreutils-6.10/src/'
    klee_command = 'klee --simplify-sym-indices --write-cov --write-smt2s --output-module --max-memory=1000 --disable-inlining --optimize --use-forked-solver --use-cex-cache --libc=uclibc --posix-runtime --allow-external-sym-calls --only-output-states-covering-new -max-sym-array-size=4096 -max-instruction-time=%d. --max-time=%d. --watchdog --max-memory-inhibit=false --max-static-fork-pct=1 -max-static-solve-pct=1 --max-static-cpfork-pct=1 --switch-type=internal --randomize-fork --search=nurs:covnew --use-batching-search --batch-instructions=10000 '%(10, 1800)
    klee_sym_args = '--sym-args 0 2 100 --sym-files 1 100'
    
    for f in glob.glob(coreutils_path + '*.o'):
        if os.path.exists(f[:-2]):
            os.system('chmod +x ' + f[:-2])
            os.system(klee_command + '--output-dir=' + f[:-2] + '_main/ ' + f[:-2] + ' ' + klee_sym_args + ' &')

