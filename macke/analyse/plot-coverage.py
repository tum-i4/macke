import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import os, argparse, time, glob
from datetime import datetime, timedelta
from matplotlib.dates import drange
from collections import OrderedDict

def split_coverage_into_slabs(time_ticks, coverage, switch_points, agents):
    coverage_slabs = []
    time_slabs = []

    init_coverage_slab = []
    init_time_slab = []
    
    for i, t in enumerate(time_ticks):
        if t>=switch_points[0]:
            dispatch_i = i
            break
        init_time_slab.append(time_ticks[i])
        init_coverage_slab.append(coverage[i])
    
    time_slabs.append(init_time_slab)
    coverage_slabs.append(init_coverage_slab)

    time_i = dispatch_i
    switch_i = 0

    cur_time_slab = [time_ticks[0]]
    cur_coverage_slab = [coverage[0]]

    while time_i<len(time_ticks):
        if switch_i>=(len(switch_points)-1):
            cur_time_slab.append(time_ticks[time_i])
            cur_coverage_slab.append(coverage[time_i])
        elif (time_ticks[time_i]>=switch_points[switch_i] and time_ticks[time_i]<switch_points[switch_i + 1]):
            cur_time_slab.append(time_ticks[time_i]) 
            cur_coverage_slab.append(coverage[time_i])
        else:
            print ("time_i: " + str(time_i))
            print (time_ticks[time_i])
            print (coverage[time_i])
            print (agents[switch_i])
            print ("")
            cur_time_slab.append(time_ticks[time_i])
            cur_coverage_slab.append(coverage[time_i])
            time_slabs.append(cur_time_slab)
            coverage_slabs.append(cur_coverage_slab)
            
            cur_time_slab = [time_ticks[time_i]]
            cur_coverage_slab = [coverage[time_i]]
            switch_i += 1

        time_i += 1
    
    time_slabs.append(cur_time_slab)
    coverage_slabs.append(cur_coverage_slab)

    return time_slabs, coverage_slabs

def parse_switch_points(output_dir):
    '''
    switch_points, agents = [], []
    log_file = open(os.path.join(output_dir, "jolf.log"), "r")

    log_lines = log_file.readlines()
    
    line_ptr = 0
    for i, l in enumerate(log_lines):
        fields = l.strip().split("2018:")
        if len(fields)==1:
            continue
        if fields[1].strip().startswith("Dispatch method"):
            line_ptr = i
            break

    while line_ptr<len(log_lines):
        fields = log_lines[line_ptr].strip().split("2018:")
        if len(fields)==1:
            line_ptr += 1
            continue
        if fields[1].strip().startswith("Calling AFL"):
            switch_points.append(datetime.strptime(fields[0].strip()+" 2018", "%a %b %d %H:%M:%S %Y"))
            agents.append("AFL")
        if fields[1].strip().startswith("Calling KLEE"):
            switch_points.append(datetime.strptime(fields[0].strip()+" 2018", "%a %b %d %H:%M:%S %Y"))
            agents.append("KLEE")

        line_ptr += 1

    return switch_points, agents
    '''
    switch_points, agents = [], []
    #print (output_dir)
    log_file = open(os.path.join(output_dir, "coverage.log"), "r")
    
    log_lines = log_file.readlines()
    was_klee = False
    if log_lines:
      fields = log_lines[0].split(',')
      if fields[1].strip() != "KLEE":
         print (fields[1].strip())
         was_klee = True
    
    for line in log_lines:
      fields = line.split(',')
      #print (fields)
      if not was_klee:
        #print (fields[1])
        if fields[1].strip() == "KLEE":
          was_klee = True
          agents.append("KLEE")
          switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))
      else: # was_klee
        if fields[1].strip() == "AFL":
          was_klee = False
          agents.append("AFL")
          switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))
    
    line = log_lines[len(log_lines)-1]
    fields = line.split(',')
    agents.append(fields[1].strip())
    switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))          
    print (switch_points)
    print (agents)      
    return switch_points, agents

def parse_coverage(output_dir, allowed_filenames):
    coverage_file = os.path.join(output_dir, "coverage.log")
    if not os.path.isfile(coverage_file):
        print("coverage.log file not found in that directory")
        return [], [], []
    
    times, lines, agents = [], [], []
    coverage = open(coverage_file)
    for line in coverage:
        #basename = line.split("2018:")[1].split(":")[1].strip().split()[0] # Only the filename, not the line number
        time_s, agent, basename, instr = [ v.strip() for v in line.strip().split(",") ]

        if int(instr)==0:
            continue

        if basename not in allowed_filenames:
            print("%s not in allowed_filenames"%(basename))
            continue

        times.append(datetime.strptime(time_s, "%a %b %d %H:%M:%S %Y"))
        lines.append(basename)
        agents.append(agent)

    #print (times)
    return times, lines, agents

def group_lines_by_time(times):
    start_time = times[0] - timedelta(minutes=5)
    stop_time = start_time + timedelta(hours=1.2)
    delta = timedelta(minutes=1)

    cur_time = start_time
    i = 0
    time_ticks = [cur_time]
    coverage = [0]

    #times_to_lines[cur_time] = (None, 0)
    while cur_time<=stop_time:
        while i<len(times) and cur_time>=times[i]: # Collect the whole lot of the coverage between cur_time-delta to cur_time
            coverage[-1] += 1
            i += 1
            
        # Now flatten out the curve till the next set of increasing slope is found
        coverage.append(coverage[-1])
        cur_time += delta
        time_ticks.append(cur_time)

    return time_ticks,coverage 

def get_allowed_filenames(allowed_list):
    allowed_filenames = []
    #print (allowed_list)
    for a in allowed_list:
        basenames = []
        for fn in glob.glob(a):
            basenames.append(os.path.basename(fn))

        allowed_filenames.extend(basenames)

    print (allowed_filenames)

    return allowed_filenames

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Time-wise coverage plotter")
    parser.add_argument("-d", "--jolf-results-dir", help="Directory containing results from Jolf")
    parser.add_argument("-o", "--output-dir", help="Where to store the plots")

    args = parser.parse_args()

    allowed_filenames = get_allowed_filenames(["/home/vintila/sources/*/*/*.c", "/home/vintila/sources/*/*/*.h"])
    #print(allowed_filenames)

    times, lines, agents = parse_coverage(args.jolf_results_dir, allowed_filenames)

    time_ticks, coverage = group_lines_by_time(times)

    switch_points, agents = parse_switch_points(args.jolf_results_dir)

    time_slabs, coverage_slabs = split_coverage_into_slabs(time_ticks, coverage, switch_points, agents)
    print ("Agents: " + str(len(agents)) + " - " + str(agents))
    print ("Time slabs: " + str(len(time_slabs)) + " - " + str(time_slabs))
    print ("Cov slabs: " + str(len(coverage_slabs)) + " - " + str(coverage_slabs))
    
    agents = ["KLEE"] + agents

    fig, ax = plt.subplots()

    for i in range(len(time_slabs)):
        print(time_slabs[i][0])
        print(time_slabs[i][-1])

        if agents[i]=="AFL":
            color = 'b-'
        elif agents[i]=="KLEE":
            color = 'g-'
        #print (agents[i] + ": " + str(time_slabs[i]) + ", " + str(coverage_slabs[i]))
        ax.plot(time_slabs[i], coverage_slabs[i], color)
        print("")
        
    #legend = ax.legend(loc='upper right')

    plot_name = os.path.basename(args.jolf_results_dir) + ".png"
    plt.savefig(os.path.join(args.output_dir, plot_name))
    
    print (args.output_dir + "/" + plot_name)
