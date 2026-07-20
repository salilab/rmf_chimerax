To build on Mac (use both a 12.0 Intel machine, and a 12.1 M1 machine, to
match ChimeraX's build environments, and install Python 3.14 and NumPy 2.4.6):

```
conda create --name=py314 python=3.14
conda activate py314
pip install numpy==2.4.6
git clone https://github.com/salilab/rmf.git
cd rmf
mkdir build && cd build
cmake .. -GNinja -DCMAKE_BUILD_TYPE=Release -DLog4CXX_LIBRARY=Log4CXX_LIBRARY-NOTFOUND -DPython3_EXECUTABLE=$(which python3.14) && ninja
PYTHONPATH=lib python3.14 ../test/test_numpy.py
```

Use `python3 make_dist.py` to collect all needed files (RMF itself plus
the dynamic libraries it uses) in the `x86_64` and `arm64` directories.

Finally, run `python3 make_universal.py` to make the final `dist` directory
containing universal binaries.
