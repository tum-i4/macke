# MACKE - `M`odular `a`nd `C`ompositional Analysis with `K`LEE `E`ngine

(A mirror of this repo is hosted at https://gitlab.lrz.de/saahil/macke)

MACKE is a wrapper around [KLEE](https://klee.github.io/), that decomposes the analyzed programs into several smaller units, analyze these seperately and finally merge all found errors to one interactive report. Please read the [MACKE-paper](https://www.researchgate.net/publication/305641321_MACKE_-_Compositional_Analysis_of_Low-Level_Vulnerabilities_with_Symbolic_Execution) for more details.

## Installation guide

### Requirements
* Python 3.4+
* A system able to run LLVM. See [official requirements for LLVM](http://www.llvm.org/docs/GettingStarted.html#requirements)

### Step 1: LLVM and KLEE with targeted search
Building KLEE can be a complicated task and there are multiple strategies for it. We suggest the setup described in our [Step-by-Step manual](https://github.com/hutoTUM/install-klee). But whatever way you choose, MACKE needs a special search mode, that is not part of the official KLEE code, yet. We aim to merge it into KLEE someday, but till then, you need to use [our fork of KLEE](https://github.com/tum-i22/klee22) and checkout its **sonar** branch.

For our step-by-step manual, this means, that you have to adapt one command. Instead of:
```
git clone --depth 1 --branch v1.3.0 https://github.com/klee/klee.git
```
in [Step 6](https://github.com/hutoTUM/install-klee#step-6-klee), you must use:
```
git clone --depth 1 --branch sonar https://github.com/tum-i22/klee22.git
```

### Step 2: Building the macke-llvm-opt passes
MACKE performs several modifications on LLVM bitcode level. Doing this inside python requires a lot more effort, than directly writing the operations in C++ - especially if you are forced to use the same, old version of LLVM as KLEE uses. Therefore, we decide to seperate all low level operations into [another repository](https://github.com/hutoTUM/macke-opt-llvm).

If you choose a different directory structure than suggested in our Step-by-Step manual, please adapt the pathes to match your needs.

```
git clone --depth 1 https://github.com/tum-i22/macke-opt-llvm 
cd macke-opt-llvm
make LLVM_SRC_PATH=~/build/llvm/ KLEE_BUILDDIR=~/build/klee/Release+Asserts KLEE_INCLUDES=~/build/klee/include/

# and if you want to run some tests before executing
make integrationtest LLVM_SRC_PATH=~/build/llvm/ KLEE_BUILDDIR=~/build/klee/Release+Asserts KLEE_INCLUDES=~/build/klee/include/
```

### Step 3: Building MACKE
We are done with the dependencies - now to the main project.
```
git clone --depth 1 https://github.com/tum-i22/macke
cd macke
make dev
```

### Step 4: Running MACKE
Before you can actually start using MACKE, you have to modify the `./config.ini` with your favorite text editor. Please adapt the pathes there to the directories, you have created earlier in this guide. Afterwards you can run:
```
source .venv/bin/activate  # Note: just needed once per open shell
macke 2beAnalyzed.bc
```

We wish you happy testing! If you have problems converting existing source code bases to bitcode files, you should have a look at this [tool for improving make](https://github.com/hutoTUM/MakeAdditions).


## Author's note

Email [HuTo](mailto:t.hutzelmann@tum.de) or [me](mailto:ognawala@in.tum.de) if something is broken. Ditto if you would like to contribute!

> [Saahil Ognawala](https://www.i22.in.tum.de/index.php?id=31&L=1)
