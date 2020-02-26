import contextlib
import sys
import tempfile
import shutil
import os


# If we're using the real ChimeraX with --nogui, we can't run GUI tests;
# if we're using mocks, a mock GUI is available so we can run these tests.
no_gui = 'RMF_DISABLE_CHIMERAX_MOCK' in os.environ

def set_search_paths(topdir):
    """Set search paths so that we can import Python modules and use mocks"""
    paths = [topdir]
    if 'RMF_DISABLE_CHIMERAX_MOCK' not in os.environ:
        paths.append(os.path.join(topdir, 'test', 'mock'))
    if 'RMF_DISABLE_QT_MOCK' not in os.environ:
        paths.append(os.path.join(topdir, 'test', 'mock-qt'))
    os.environ['PYTHONPATH'] = os.pathsep.join(paths
                                         + [os.environ.get('PYTHONPATH', '')])
    for p in reversed(paths):
        sys.path.insert(0, p)


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

class _MockUi:
    pass

def make_session():
    import chimerax.core.session
    import chimerax.core.core_triggers
    import chimerax.core.tools
    s = chimerax.core.session.Session('test')
    chimerax.core.core_triggers.register_core_triggers(s.triggers)
    s.ui = _MockUi()
    s.ui.is_gui = not no_gui
    s.tools = chimerax.core.tools.Tools(s, first=True)
    return s
