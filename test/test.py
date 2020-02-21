import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src
import src.io


INDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'input'))

RMF = utils.import_rmf_module()


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

    def test_bundle_api_open(self):
        """Test open file via BundleAPI"""
        bundle_api = src.bundle_api
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = MockSession()
        structures, status = bundle_api.open_file(mock_session, path, 'RMF')

    def test_read_geometry(self):
        """Test open_rmf handling of RMF geometry"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()
            sf = RMF.SegmentFactory(r)

            s = sf.get(rn.add_child("test segment", RMF.GEOMETRY))
            s.set_coordinates_list([RMF.Vector3(0, 0, 0), RMF.Vector3(5, 5, 5)])

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = MockSession()
            structures, status = src.io.open_rmf(mock_session, fname)
            # One shape should have been added
            shapes = structures[0]._drawing._drawing._shapes
            self.assertEqual(len(shapes), 1)


if __name__ == '__main__':
    unittest.main()
