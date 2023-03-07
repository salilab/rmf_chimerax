To build on Mac (use both a 10.15 Intel machine, and a 12.1 M1 machine,
to match ChimeraX's build environments, and install Python 3.9):

```
git clone https://github.com/salilab/rmf.git
cd rmf
mkdir build && cd build
cmake .. -GNinja -DCMAKE_BUILD_TYPE=Release -DLog4CXX_LIBRARY=Log4CXX_LIBRARY-NOTFOUND -DPython3_EXECUTABLE=$(which python3.9) && ninja
```

Use `python3 make_dist.py` to collect all needed files (RMF itself plus
the dynamic libraries it uses) in the `x86_64` and `arm64` directories.

Finally, run `python3 make_universal.py` to make the final `dist` directory
containing universal binaries.
