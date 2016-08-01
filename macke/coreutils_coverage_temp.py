from .source_coverage import source_coverage, get_source_coverage
import glob, os

cov_main = []
seen_main = []

cov_comp = []
seen_comp = []

for c in glob.glob('/mnt/ext-hdd/coreutils-6.10/src/*.c'):
    if os.path.exists(c[:-2]+'_main/'):
        cov_temp, seen_temp = get_source_coverage(c, c[:-2]+'_main/run.istats', [], [])
        cov_main.extend(cov_temp)
        seen_main.extend(seen_temp)

    cov_temp, seen_temp = source_coverage(c)
    cov_comp.extend(cov_temp)
    seen_comp.extend(seen_temp)

print(len(cov_main), len(seen_main))
print(len(cov_comp), len(seen_comp))
