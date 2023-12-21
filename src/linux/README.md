To build on Linux (use a RHEL7 machine to match ChimeraX's build environment):

```
yum install git python311 swig3 boost-devel hdf5-devel gcc-c++ ninja cmake chrpath sali-modules
source /etc/profile
module load python3/numpy
ln -sf python3.11 /usr/bin/python3
git clone https://github.com/salilab/rmf.git
cd rmf
mkdir build && cd build
cmake .. -GNinja -DCMAKE_BUILD_TYPE=Release && ninja
PYTHONPATH=lib:$PYTHONPATH python3.11 ../test/test_numpy.py
```

Use `python3 make_dist.py` to collect all needed files (RMF itself plus
the dynamic libraries it uses) in the `dist` directory.
