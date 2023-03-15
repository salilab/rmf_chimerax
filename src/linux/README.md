To build on Linux (use a RHEL7 machine to match ChimeraX's build environment):

```
git clone https://github.com/salilab/rmf.git
cd rmf
mkdir build && cd build
cmake .. -GNinja -DCMAKE_BUILD_TYPE=Release && ninja
PYTHONPATH=lib python3.9 ../test/test_numpy.py
```

Use `python3 make_dist.py` to collect all needed files (RMF itself plus
the dynamic libraries it uses) in the `dist` directory.
