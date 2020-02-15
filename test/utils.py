import sys
import os


def set_search_paths(topdir):
    """Set search paths so that we can import Python modules and use mocks"""
    mockdir = os.path.join(topdir, 'test', 'mock')
    os.environ['PYTHONPATH'] = topdir + os.pathsep + mockdir + os.pathsep \
                               + os.environ.get('PYTHONPATH', '')
    sys.path.insert(0, mockdir)
    sys.path.insert(0, topdir)
