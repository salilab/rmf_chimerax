import contextlib
import sys
import tempfile
import shutil
import os


def set_search_paths(topdir):
    """Set search paths so that we can import Python modules and use mocks"""
    mockdir = os.path.join(topdir, 'test', 'mock')
    os.environ['PYTHONPATH'] = topdir + os.pathsep + mockdir + os.pathsep \
                               + os.environ.get('PYTHONPATH', '')
    sys.path.insert(0, mockdir)
    sys.path.insert(0, topdir)


@contextlib.contextmanager
def temporary_file(suffix):
    """Make a named temporary file, deleted at the end of the 'with' block"""
    fd, fname = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    yield fname
    os.unlink(fname)


def import_rmf_module():
    """Import and return the copy of RMF included in the bundle"""
    if sys.platform == 'darwin':
        from src.mac import RMF
    elif sys.platform == 'linux':
        from src.linux import RMF
    else:
        from src.windows import RMF
    return RMF
