import subprocess
import shutil
import os

wanted_libs = ['lib/_RMF_HDF5.so', 'lib/_RMF.so']
wanted_py = ['lib/RMF_HDF5.py', 'lib/RMF.py']
dist = 'dist'


def get_deps(lib):
    out = subprocess.check_output(['ldd', lib],
                                  universal_newlines=True).split('\n')
    for line in out:
        if '=>' in line:
            dep = line.split('=>')[1].split()[0].strip()
            if 'not found' in dep:
                raise ValueError(line)
            if ((not dep.startswith('/lib64/') and not dep.startswith('('))
                or 'boost' in dep or 'hdf5' in dep or 'libsz' in dep):
                yield dep


def set_loader_path(lib):
    cmd = ['chrpath', '-r', '$ORIGIN', lib]
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def copy_lib(lib, dest):
    destlib = os.path.join(dest, os.path.basename(lib))
    if os.path.exists(destlib):
        return
    shutil.copy(lib, dest)
    os.chmod(destlib, 0o755)

    for dep in get_deps(lib):
        copy_lib(dep, dest)


def main():
    if os.path.exists(dist):
        shutil.rmtree(dist)
    os.mkdir(dist)


    for py in wanted_py:
        shutil.copy(py, dist)

    for lib in wanted_libs:
        copy_lib(lib, dist)
        set_loader_path(os.path.join(dist, os.path.basename(lib)))


if __name__ == '__main__':
    main()
