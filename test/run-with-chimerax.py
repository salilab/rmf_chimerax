# This script runs the unit tests within the ChimeraX environment.
# Normally the scripts are run with "python3 -m nose test" which mocks
# ChimeraX, but they can also be run within ChimeraX itself.

# Normally this is run from the top-level Makefile with "make test-chimerax"

import unittest
import sys
import os
import importlib.machinery


def load_module(fname):
    name, ext = os.path.splitext(fname)
    return importlib.machinery.SourceFileLoader(name, fname).load_module()


class MyTestProgram(unittest.TestProgram):
    def createTests(self, from_discovery=False, Loader=None):
        # Override default unittest behavior; instead, test all given files
        tests = [t for t in sys.argv[1:] if '-' not in t]
        # Add path containing tests to Python search path so 'import utils'
        # works
        test_dir = os.path.abspath(os.path.dirname(tests[0]))
        sys.path.insert(0, test_dir)
        # Disable mocks; use ChimeraX and Qt directly
        os.environ['RMF_DISABLE_CHIMERAX_MOCK'] = '1'
        os.environ['RMF_DISABLE_QT_MOCK'] = '1'
        modobjs = [load_module(m) for m in tests]
        self.test = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromModule(o) for o in modobjs)

MyTestProgram(argv=[sys.argv[0]], verbosity=2)
