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
    
    # init_time when analysis has not started yet
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

    cur_time_slab = [time_ticks[time_i-1], time_ticks[time_i]]
    cur_coverage_slab = [coverage[time_i-1], coverage[time_i]]

    while time_i<len(time_ticks):
        if switch_i>=(len(switch_points)-1): # Passed all switch points
            cur_time_slab.append(time_ticks[time_i])
            cur_coverage_slab.append(coverage[time_i])
        elif (time_ticks[time_i]>=switch_points[switch_i] and time_ticks[time_i]<switch_points[switch_i + 1]): # In between switch points
            cur_time_slab.append(time_ticks[time_i]) 
            cur_coverage_slab.append(coverage[time_i])
        else: # Passed a switch point
            print ("time_i: " + str(time_i))
            #print (time_ticks[time_i])
            #print (coverage[time_i])
            #print (agents[switch_i])
            #print ("")
            #cur_time_slab.append(time_ticks[time_i])
            #cur_coverage_slab.append(coverage[time_i])
            time_slabs.append(cur_time_slab)
            coverage_slabs.append(cur_coverage_slab)
            
            cur_time_slab = [time_ticks[time_i-1], time_ticks[time_i]]
            cur_coverage_slab = [coverage[time_i-1], coverage[time_i]]
            switch_i += 1

        time_i += 1
    
    time_slabs.append(cur_time_slab)
    coverage_slabs.append(cur_coverage_slab)

    return time_slabs, coverage_slabs

def parse_switch_points(log_filename):
    switch_points, agents = [], []
    #print (output_dir)
    log_file = open(log_filename, "r")
    
    log_lines = log_file.readlines()
    was_klee = False
    was_afl = False
    klee_running = False
    afl_running = False

    fields = log_lines[0].split(",")
    
    switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))
    
    if fields[1].strip() == "KLEE":
        klee_running = True
        agents.append("KLEE")
    elif fields[1].strip() == "AFL":
        afl_running = True
        agents.append("AFL")
    else:
        print("Unknown agent found: %s"%(fields[1].strip()))
        return [], []
    
    for line in log_lines:
        fields = line.split(',')
        #print (fields)
        agent = fields[1].strip()
        if agent=="KLEE" and afl_running:
            afl_running = False
            klee_running = True
            agents.append("KLEE")
            switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))
        if agent=="AFL" and klee_running:
            klee_running = False
            afl_running = True
            agents.append("AFL")
            switch_points.append(datetime.strptime(fields[0].strip(), "%a %b %d %H:%M:%S %Y"))
        
    """
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
    """
    
    print (switch_points)
    print (agents)      
    return switch_points, agents

def parse_coverage(coverage_file, allowed_filenames):
    if not os.path.isfile(coverage_file):
        print("coverage content not found")
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
    start_time = times[0] - timedelta(seconds=15)
    stop_time = start_time + timedelta(minutes=3)
    delta = timedelta(seconds=1)

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
        last_coverage = coverage[-1]
        coverage.append(last_coverage)
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
    #parser.add_argument("-d", "--jolf-results-dir", help="Directory containing results from Jolf")
    parser.add_argument("-o", "--output-dir", help="Where to store the plots")
    parser.add_argument("-c", "--coverage-file", help="File containing coverage")

    args = parser.parse_args()

    allowed_filenames = get_allowed_filenames(["/home/vintila/sources/*/*/*.c", "/home/vintila/sources/*/*/*.h"])
    #print(allowed_filenames)

    times, lines, agents = parse_coverage(args.coverage_file, allowed_filenames)

    time_ticks, coverage = group_lines_by_time(times)
    """
    for i, t in enumerate(time_ticks):
        print(str(t) + ": " + str(coverage[i]))
    """
    switch_points, agents = parse_switch_points(args.coverage_file)

    time_slabs, coverage_slabs = split_coverage_into_slabs(time_ticks, coverage, switch_points, agents)
    #print ("Agents: " + str(len(agents)) + " - " + str(agents))
    #print ("Time slabs: " + str(len(time_slabs)) + " - " + str(time_slabs))
    #print ("Cov slabs: " + str(len(coverage_slabs)) + " - " + str(coverage_slabs))
    
    agents = [agents[0]] + agents

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

    plot_name = os.path.basename(args.coverage_file) + ".png"
    plt.savefig(os.path.join(args.output_dir, plot_name))
    
    print (args.output_dir + "/" + plot_name)
