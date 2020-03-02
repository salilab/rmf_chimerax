import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src
import src.cmd
import src.io
from utils import make_session

INDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'input'))

RMF = utils.import_rmf_module()

class MockLogger(object):
    def __init__(self):
        self.info_log = []

    def info(self, msg, is_html=False):
        self.info_log.append((msg, is_html))


from chimerax.core.session import Session
class MockSession(Session):
    def __init__(self, app_name):
        super().__init__(app_name)
        self.logger = MockLogger()

class MockModel:
    id_string = '1'

class MockRMFNode:
    def __init__(self, name, index):
        self.name, self.index = name, index
    def get_name(self): return self.name
    def get_index(self): return self.index

def make_node(name, index):
    n = MockRMFNode(name, index)
    return src.io._RMFHierarchyNode(n)

def make_test_rmf_hierarchy():
    root = make_node("root", 0)
    child1 = make_node("child1", 1)
    child2 = make_node("child2", 2)
    grandchild1 = make_node("grandchild1", 3)
    grandchild2 = make_node("grandchild2", 4)
    root.children.extend((child1, child2))
    child1.children.extend((grandchild1, grandchild2))
    test_model = MockModel()
    test_model.rmf_hierarchy = root
    return test_model


class Tests(unittest.TestCase):
    def test_register(self):
        """Test register of rmf commands"""
        class MockCommandInfo:
            def __init__(self, name, synopsis):
                self.name, self.synopsis = name, synopsis
        bundle_api = src.bundle_api
        ci = MockCommandInfo("rmf hierarchy", "test synopsis")
        bundle_api.register_command(None, ci, None)

        ci = MockCommandInfo("rmf chains", "test synopsis")
        bundle_api.register_command(None, ci, None)

        ci = MockCommandInfo("rmf readtraj", "test synopsis")
        bundle_api.register_command(None, ci, None)

        ci = MockCommandInfo("bad command", "test synopsis")
        self.assertRaises(ValueError, bundle_api.register_command,
                          None, ci, None)

    def test_hierarchy_not_rmf(self):
        """Test hierarchy command on a model that is not an RMF"""
        mock_session = MockSession('test')
        src.cmd.hierarchy(mock_session, 'garbage model')
        self.assertEqual(mock_session.logger.info_log, [])

    def test_hierarchy(self):
        """Test hierarchy command"""
        test_model = make_test_rmf_hierarchy()
        mock_session = MockSession('test')
        src.cmd.hierarchy(mock_session, test_model)
        (log, is_html), = mock_session.logger.info_log
        def get_li_lines(l):
            return [line[4:] for line in l.split("\n")
                    if line.startswith('<li>')]
        self.assertTrue(is_html)
        # Default depth shows everything
        self.assertEqual(get_li_lines(log),
                         ['root', 'child1', 'grandchild1',
                          'grandchild2', 'child2'])

        src.cmd.hierarchy(mock_session, test_model, depth=1)
        log, is_html = mock_session.logger.info_log[-1]
        self.assertEqual(get_li_lines(log), ['root', 'child1', 'child2'])

    def test_chains_not_rmf(self):
        """Test chains command on a model that is not an RMF"""
        mock_session = MockSession('test')
        src.cmd.chains(mock_session, 'garbage model')
        self.assertEqual(mock_session.logger.info_log, [])

    def test_chains(self):
        """Test chains command"""
        test_model = make_test_rmf_hierarchy()
        test_model._rmf_chains = [('A', test_model.rmf_hierarchy.children[0])]
        mock_session = MockSession('test')
        src.cmd.chains(mock_session, test_model)
        (log, is_html), = mock_session.logger.info_log
        self.assertIn('<td>child1</td>', log)
        self.assertIn('<td><a title="Select chain" '
                      'href="cxcmd:select #1/A">A</a></td>', log)

    def test_read_traj(self):
        """Test readtraj with a simple coarse-grained RMF file"""
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = make_session()
        mock_session.logger = MockLogger()
        structures, status = src.io.open_rmf(mock_session, path)
        state = structures[0].child_models()[0]
        src.cmd.readtraj(mock_session, state)

    def test_readtraj_not_rmf(self):
        """Test readtraj command on a model that is not an RMF"""
        mock_session = MockSession('test')
        src.cmd.chains(mock_session, 'garbage model')
        self.assertEqual(mock_session.logger.info_log, [])

    def test_read_balls(self):
        """Test readtraj handling of RMF Balls"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()
            bf = RMF.BallFactory(r)
            cf = RMF.ColoredFactory(r)

            n = rn.add_child("ball", RMF.GEOMETRY)
            b1 = bf.get(n)
            b1.set_radius(6)
            b1.set_coordinates(RMF.Vector3(1.,2.,3.))
            c1 = cf.get(n)
            c1.set_rgb_color(RMF.Vector3(1,0,0))

            b2 = bf.get(rn.add_child("ball", RMF.GEOMETRY))
            b2.set_radius(4)
            b2.set_coordinates(RMF.Vector3(4.,5.,6.))
            # no color

            r.add_frame("f1", RMF.FRAME)
            r.add_frame("f2", RMF.FRAME)

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            mock_session.logger = MockLogger()
            structures, status = src.io.open_rmf(mock_session, fname)
            state = structures[0].child_models()[0]
            # Just one frame to start with
            self.assertEqual(list(state.coordset_ids), [1])
            # Test noop read of structure
            src.cmd.readtraj(mock_session, structures[0])
            src.cmd.readtraj(mock_session, state, last=1)
            # Two frames should have been read
            self.assertEqual(list(state.coordset_ids), [1, 2])

    def test_alternatives(self):
        """Test readtraj handling of RMF alternatives"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()

            af = RMF.AlternativesFactory(r)
            pf = RMF.ParticleFactory(r)
            gf = RMF.GaussianParticleFactory(r)

            n = rn.add_child("topp1", RMF.REPRESENTATION)
            p = n.add_child("p1", RMF.REPRESENTATION)
            b = pf.get(p)
            b.set_mass(1)
            b.set_radius(4)
            b.set_coordinates(RMF.Vector3(4.,5.,6.))
            a = af.get(n)

            root = r.add_node("topp2", RMF.REPRESENTATION)
            p = root.add_child("p2", RMF.REPRESENTATION)
            b = pf.get(p)
            b.set_radius(4)
            b.set_coordinates(RMF.Vector3(4.,5.,6.))
            a.add_alternative(root, RMF.PARTICLE)

            root = r.add_node("topg1", RMF.REPRESENTATION)
            g = root.add_child("g1", RMF.REPRESENTATION)
            b = gf.get(g)
            b.set_variances(RMF.Vector3(1.,1.,1.))
            b.set_mass(1.)
            a.add_alternative(root, RMF.GAUSSIAN_PARTICLE)
            r.add_frame("f1", RMF.FRAME)
            r.add_frame("f2", RMF.FRAME)
            r.add_frame("f3", RMF.FRAME)
            r.add_frame("f4", RMF.FRAME)
            r.add_frame("f5", RMF.FRAME)

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            mock_session.logger = MockLogger()
            structures, status = src.io.open_rmf(mock_session, fname)
            state = structures[0].child_models()[0]
            # Just one frame to start with
            self.assertEqual(list(state.coordset_ids), [1])
            src.cmd.readtraj(mock_session, state, first=2, step=2)
            # Two frames (f2, f4) should have been read
            self.assertEqual(list(state.coordset_ids), [1, 3, 5])


if __name__ == '__main__':
    unittest.main()
