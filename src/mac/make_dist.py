import subprocess
import shutil
import os

wanted_libs = ['lib/_RMF_HDF5.so', 'lib/_RMF.so']
wanted_py = ['lib/RMF_HDF5.py', 'lib/RMF.py']

if os.uname().machine == 'arm64':
    dist = 'arm64'
else:
    dist = 'x86_64'


def get_deps(lib):
    libdir = os.path.dirname(lib)
    out = subprocess.check_output(['otool', '-L', lib], text=True).split('\n')
    for line in out:
        if 'compatibility version' in line:
            lib = line.split()[0]
            if not lib.startswith('/usr/lib/'):
                yield lib.replace('@loader_path', libdir)


def set_dep_loader_path(lib, dep):
    cmd = ['install_name_tool', '-change', dep,
           os.path.join('@loader_path', os.path.basename(dep)), lib]
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def set_loader_path(lib):
    cmd = ['install_name_tool', '-id',
           os.path.join('@loader_path', os.path.basename(lib)), lib]
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def copy_lib(lib, dest):
    destlib = os.path.join(dest, os.path.basename(lib))
    if os.path.exists(destlib):
        return
    shutil.copy(lib, dest)
    os.chmod(destlib, 0o755)
    set_loader_path(destlib)
    
    for dep in get_deps(lib):
        set_dep_loader_path(destlib, dep)
        copy_lib(dep, dest)


def codesign(dest):
    for lib in os.listdir(dest):
        if lib.endswith('.so') or lib.endswith('.dylib'):
            cmd = ['codesign', '-f', '-s', '-',
                   os.path.join(dest, lib)]
            print(" ".join(cmd))
            subprocess.check_call(cmd)


def main():
    if os.path.exists(dist):
        shutil.rmtree(dist)
    os.mkdir(dist)


    for py in wanted_py:
        shutil.copy(py, dist)

    for lib in wanted_libs:
        copy_lib(lib, dist)

    if os.uname().machine == 'arm64':
        codesign(dist)


if __name__ == '__main__':
    main()
