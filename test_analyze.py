from analyze_klee_test import find_ptr_errs, get_culp_line, find_matching_error

err_funcs = find_ptr_errs('/home/ognawala/stonesoup/stonesoup-c-mc/bzip2/blocksort')
print err_funcs
