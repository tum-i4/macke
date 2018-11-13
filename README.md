# MACKE - `M`odular `a`nd `C`ompositional Analysis with `K`LEE (and AFL) `E`ngine

MACKE is a wrapper around [AFL](http://lcamtuf.coredump.cx/afl/) and [KLEE](https://klee.github.io/), that decomposes the analyzed programs into several smaller units, analyze these seperately and finally merge all found errors to one interactive report. Please read the [MACKE-paper](https://www.researchgate.net/publication/305641321_MACKE_-_Compositional_Analysis_of_Low-Level_Vulnerabilities_with_Symbolic_Execution) for more details.

## Installation guide

### Requirements
* Python 3.4+
* A system able to run LLVM. See [official requirements for LLVM](http://www.llvm.org/docs/GettingStarted.html#requirements)
* AFL See AFL's [Quickstart guide](http://lcamtuf.coredump.cx/afl/QuickStartGuide.txt)

### Step 1: LLVM and KLEE with targeted search
Building KLEE can be a complicated task and there are multiple strategies for it. We suggest the setup described in our [Step-by-Step manual](https://github.com/hutoTUM/install-klee). But whatever way you choose, MACKE needs a special search mode, that is not part of the official KLEE code, yet. We aim to merge it into KLEE someday, but till then, you need to use [our fork of KLEE](https://github.com/tum-i22/klee22).

For our step-by-step manual, this means, that you have to adapt one command. Instead of:
```
git clone --depth 1 --branch v1.3.0 https://github.com/klee/klee.git
```
in [Step 6](https://github.com/hutoTUM/install-klee#step-6-klee), you must use:
```
git clone --depth 1 https://github.com/tum-i22/klee22.git
```

In addition to the above, you also need to install LLVM 6.0 if you want the ability to fuzz in phase 1 of Macke. 

For our step-by-step manual, this means that you must **repeat** [Step 1](https://github.com/tum-i22/klee-install#step-1-llvm) for LLVM 6.0, i.e. replace ``RELEASE_342`` with ``RELEASE_600`` in all links. 

### Step 2: Building the macke-llvm-opt passes
MACKE performs several modifications on LLVM bitcode level. Doing this inside python requires a lot more effort, than directly writing the operations in C++ - especially if you are forced to use the same, old version of LLVM as KLEE uses. Therefore, we decide to seperate all low level operations into two other repositories - [one for LLVM 3.4 for KLEE-related stuff](https://github.com/hutoTUM/macke-opt-llvm) and [another one for LLVM 6.0 for AFL-related stuff](https://github.com/tum-i22/macke-fuzzer-opt-llvm). 

If you choose a different directory structure than suggested in our Step-by-Step manual, please adapt the pathes to match your needs.

```
git clone --depth 1 https://github.com/tum-i22/macke-opt-llvm 
cd macke-opt-llvm
make LLVM_SRC_PATH=~/build/llvm3.4/ KLEE_BUILDDIR=~/build/klee/Release+Asserts KLEE_INCLUDES=~/build/klee/include/
```

Now repeat the above step for macke-fuzzer-opt-llvm 
```
git clone --depth 1 https://github.com/tum-i22/macke-fuzzer-opt-llvm 
cd macke-fuzzer-opt-llvm
make LLVM_SRC_PATH=~/build/llvm6.0/ KLEE_BUILDDIR=~/build/klee/Release+Asserts KLEE_INCLUDES=~/build/klee/include/
```

### Step 3: Building MACKE
We are done with the dependencies - now to the main project.
```
# You might have to change the branch in repository below, depending on the version you want to build
git clone --depth 1 https://github.com/tum-i22/macke
cd macke
make dev
```

### Step 4: Running MACKE
Before you can actually start using MACKE, you have to modify the `./config.ini` with your favorite text editor. Please adapt the pathes there to the directories, you have created earlier in this guide. 

First switch your virtual environment to Macke

```
source .venv/bin/activate # Note: just needed once per open shell
```

If you want to analyze the isolated functions with symbolic execution then run the following:
```
macke 2beAnalyzed.bc
```

Otherwise if you want to analyze the isolated functions with fuzzing (AFL) then run the following:
```
macke --use-fuzzer=1 --fuzz-bc=2beAnalyzedCompiledWithClang3.8.bc 2beAnalyzed.bc
```

We wish you happy testing! If you have problems converting existing source code bases to bitcode files, you should have a look at this [tool for improving make](https://github.com/tum-i22/MakeAdditions).

## Troubleshooting

# Getting around the issue of cgroups
Linux control groups, or *Cgroups* in short, are a kernel feature that allows user space processes to have limited (and exclusive) access to certain system resources, such as CPU. We leverage cgroups to isolate parallel fuzzing processes so that they don't interfere. 

Therefore, before using Macke, you need to create these cgroups partitions. There are two alternative ways to do this. 

__Alternative 1: Using Macke__

1. Change as root 
```
sudo -s
```

2. Load macke (with source command) virtual environment and create cgroups
```
macke --initialize-cgroups --cgroup-name=<user>:<group>
```

If the warning about limiting swap memory shows up, then run the following
```
macke --initialize-cgroups --cgroup-name=<user>:<group> --ignore-swap
```
and in all subsequent macke commands, also add --ignore-swap

__Alternative 2: Manually on command-line__:

1. Run cgroups command. 
If your CPU has *x* cores, then run the following command *x* times replacing the index *i* with the CPU number, i.e. *mackefuzzer_1*, *mackefuzzer_2*... *mackefuzzer_x*. 

```
cgcreate -s 775 -d 775 -f 775 -a <usergroup> -t <usergroup> -g memory: mackefuzzer_<i>
```

You almost certainly might need to run this command as root or with sudo. 

Then, in all subsequent macke commands, also add --ignore-swap, if your operating system does not allow partitioning swap memory resource. 

## Author's note
For current issues, suggestions, datasets and gratitude please email [me](mailto:saahil.ognawala@tum.de). 
Big thanks to [HuTo](t.hutzelmann@tum.de) and [Fabian Kilger](fabian.kilger@tum.de) for most of the development effort. 

> [Saahil Ognawala](https://www22.in.tum.de/en/ognawala/)
