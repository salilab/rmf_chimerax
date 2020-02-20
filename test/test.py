import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src
import src.io


INDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'input'))


class MockSession(object):
    pass


class Tests(unittest.TestCase):
    def test_open_rmf(self):
        """Test open_rmf with a simple coarse-grained RMF file"""
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = MockSession()
        structures, status = src.io.open_rmf(mock_session, path)

    def test_open_rmf_atomic(self):
        """Test open_rmf with a simple atomic RMF file"""
        path = os.path.join(INDIR, 'simple_atomic.rmf3')
        mock_session = MockSession()
        structures, status = src.io.open_rmf(mock_session, path)


if __name__ == '__main__':
    unittest.main()
