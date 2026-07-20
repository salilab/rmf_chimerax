To build on Linux (use a Rocky 8 machine to match ChimeraX's build environment):

```
dnf config-manager --set-enabled powertools
dnf install ninja-build --disablerepo salilab
dnf install git python314 swig boost-devel hdf5-devel hdf5-static gcc-c++ cmake chrpath
source /etc/profile
cd
curl -LO https://files.pythonhosted.org/packages/5d/6c/7f237821c9642fb2a04d2f1e88b4295677144ca93285fd76eff3bcba858d/numpy-2.4.2-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
(cd /usr/lib64/python3.14/site-packages/ && unzip ~/numpy-2.4.2-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl)
ln -sf python3.14 /usr/bin/python3
git clone https://github.com/salilab/rmf.git
cd rmf
mkdir build && cd build
cmake .. -GNinja -DCMAKE_BUILD_TYPE=Release && ninja
PYTHONPATH=lib:$PYTHONPATH python3.14 ../test/test_numpy.py
```

Use `python3 make_dist.py` to collect all needed files (RMF itself plus
the dynamic libraries it uses) in the `dist` directory.
