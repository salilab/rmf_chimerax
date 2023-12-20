import os
import subprocess
import shutil


dest = 'dist'
srcs = ['arm64', 'x86_64']
pythons = ['RMF_HDF5.py', 'RMF.py']
libs = ['libboost_iostreams-mt.dylib', 'libboost_system-mt.dylib', '_RMF.so',
        'libboost_thread-mt.dylib', '_RMF_HDF5.so', 'libhdf5.310.dylib',
        'libRMF.1.6.dylib', 'liblzma.5.dylib', 'libboost_atomic-mt.dylib',
        'libsz.2.dylib', 'libboost_filesystem-mt.dylib', 'libzstd.1.dylib']


def check_files(src):
    files = os.listdir(src)
    if sorted(files) != sorted(pythons + libs):
        raise ValueError("Unexpected files found in " + src)


def diff_python(py):
    contents = []
    for src in srcs:
        with open(os.path.join(src, py)) as fh:
            contents.append(fh.read())
    if contents[0] != contents[1]:
        raise ValueError("%s differs between %s and %s"
                         % (py, srcs[0], srcs[1]))


def make_universal():
    for src in srcs:
        check_files(src)
    for py in pythons:
        diff_python(py)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.mkdir(dest)
    for py in pythons:
        shutil.copy(os.path.join(srcs[0], py), dest)
    for lib in libs:
        subprocess.check_call(
            ['lipo', '-create', '-output', os.path.join(dest, lib),
             os.path.join(srcs[0], lib), os.path.join(srcs[1], lib)])


if __name__ == '__main__':
    make_universal()
