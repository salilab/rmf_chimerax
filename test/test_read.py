import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src
import src.io
from utils import make_session

INDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'input'))

RMF = utils.import_rmf_module()

from chimerax.atomic import Pseudobond

def get_all_nodes(structure):
    """Yield all RMF nodes in a given structure, by flattening the hierarchy"""
    def get_node(node):
        yield node
        for child in node.children:
            for node in get_node(child):
                yield node
    return get_node(structure.rmf_hierarchy)


class Tests(unittest.TestCase):
    def test_open_rmf(self):
        """Test open_rmf with a simple coarse-grained RMF file"""
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = make_session()
        # Exercise no-gui branch
        mock_session.ui.is_gui = False
        structures, status = src.io.open_rmf(mock_session, path)
        state, = structures[0].child_models()
        self.assertFalse(state._atomic)
        state.apply_auto_styling()
        # Check hierarchy
        nodes = list(get_all_nodes(structures[0]))
        self.assertEqual([n.name for n in nodes],
            ['root', 'System', 'State_0', 'Rpb1', 'Frag_1-20',
             'Frag_1-20: Res 10', '1-10_bead', '11-20_bead', 'bonds', 'bond'])
        # Check features
        self.assertEqual([n.name for n in structures[0].rmf_features],
                         ['|Chen|0.1|Rpb1|1|Rpb1|18|0|PSI|'])
        # Check provenance
        self.assertEqual([n.name for n in structures[0].rmf_provenance],
                         ["Sampling using Monte Carlo making 50 frames"])
        s = structures[0].rmf_provenance[0]
        self.assertIn('Using script ', s.previous.name)
        self.assertEqual(s.previous.previous.name,
            'Using software IMP PMI module version develop-d9b88ed5a1 from '
            'https://integrativemodeling.org')
        self.assertEqual(s.previous.previous.previous.name,
            'Using software Integrative Modeling Platform (IMP) version '
            'develop-d9b88ed5a1 from https://integrativemodeling.org')
        self.assertIsNone(s.previous.previous.previous.previous)
        # Check chains
        chains = structures[0]._rmf_chains
        self.assertEqual(len(chains), 1)
        self.assertEqual(chains[0][0], 'A')
        self.assertEqual(chains[0][1].name, 'Rpb1')

    def test_open_rmf_atomic(self):
        """Test open_rmf with a simple atomic RMF file"""
        path = os.path.join(INDIR, 'simple_atomic.rmf3')
        mock_session = make_session()
        structures, status = src.io.open_rmf(mock_session, path)
        state, = structures[0].child_models()
        self.assertTrue(state._atomic)
        state.apply_auto_styling()

    def test_bundle_api_open(self):
        """Test open file via BundleAPI"""
        bundle_api = src.bundle_api
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = make_session()
        structures, status = bundle_api.open_file(mock_session, path, 'RMF')

    def test_read_features(self):
        """Test open_rmf handling of RMF features"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()
            rf = RMF.RepresentationFactory(r)
            bf = RMF.BallFactory(r)

            n1 = rn.add_child("ball1", RMF.GEOMETRY)
            b1 = bf.get(n1)
            b1.set_radius(6)
            b1.set_coordinates(RMF.Vector3(1.,2.,3.))

            n2 = rn.add_child("ball2", RMF.GEOMETRY)
            b2 = bf.get(n2)
            b2.set_radius(6)
            b2.set_coordinates(RMF.Vector3(4.,5.,6.))

            n3 = rn.add_child("ball3", RMF.GEOMETRY)
            b3 = bf.get(n3)
            b3.set_radius(6)
            b3.set_coordinates(RMF.Vector3(7.,8.,9.))

            f = rf.get(rn.add_child("feat 1", RMF.FEATURE))
            f.set_representation([n1.get_id(), n2.get_id()])

            f = rf.get(rn.add_child("feat 2", RMF.FEATURE))
            f.set_representation([n2.get_id(), n3.get_id()])

            # 3-particle feature (should be ignored)
            f = rf.get(rn.add_child("feat 2", RMF.FEATURE))
            f.set_representation([n1.get_id(), n2.get_id(), n3.get_id()])

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            # Three features should have been added
            features = structures[0].rmf_features
            self.assertEqual(len(features), 3)
            self.assertIsInstance(features[0].chimera_obj, Pseudobond)
            self.assertIsInstance(features[1].chimera_obj, Pseudobond)
            self.assertIsNone(features[2].chimera_obj)

    def test_read_geometry(self):
        """Test open_rmf handling of RMF geometry"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()
            sf = RMF.SegmentFactory(r)

            s = sf.get(rn.add_child("test segment", RMF.GEOMETRY))
            s.set_coordinates_list([RMF.Vector3(0, 0, 0), RMF.Vector3(5, 5, 5)])

            s = sf.get(rn.add_child("test segment2", RMF.GEOMETRY))
            s.set_coordinates_list([RMF.Vector3(0, 0, 0), RMF.Vector3(5, 5, 5)])

            # Segments are ignored unless they contain two points
            s = sf.get(rn.add_child("test segment2", RMF.GEOMETRY))
            s.set_coordinates_list([RMF.Vector3(0, 0, 0), RMF.Vector3(5, 5, 5),
                                    RMF.Vector3(10, 10, 10)])

            # Lines with zero length are ignored
            s = sf.get(rn.add_child("null segment", RMF.GEOMETRY))
            s.set_coordinates_list([RMF.Vector3(0, 0, 0), RMF.Vector3(0, 0, 0)])

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            # Two shapes should have been added
            shapes = structures[0]._drawing._drawing._shapes
            self.assertEqual(len(shapes), 2)

    def test_read_balls(self):
        """Test open_rmf handling of RMF Balls"""
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


        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            # Two atoms (in a single residue in the unnamed state)
            # should have been added
            state, = structures[0].child_models()
            self.assertEqual(len(state.residues), 1)
            self.assertEqual(len(state.atoms), 2)

            a1, a2 = state.atoms
            # Default element
            self.assertEqual(a1.element.name, 'C')
            self.assertEqual(a2.element.name, 'C')
            self.assertEqual([int(c) for c in a1.coord], [1,2,3])
            self.assertEqual([int(c) for c in a2.coord], [4,5,6])

    def test_read_atoms_het(self):
        """Test open_rmf handling of RMF atoms with HET prefix"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()
            atomf = RMF.AtomFactory(r)
            particlef = RMF.ParticleFactory(r)
            chainf = RMF.ChainFactory(r)
            residuef = RMF.ResidueFactory(r)
            n = rn.add_child("H", RMF.REPRESENTATION)
            c = chainf.get(n)
            c.set_chain_id('H')

            def add_residue(n, atom_name, resnum, res_name):
                n = n.add_child("%d" % resnum, RMF.REPRESENTATION)
                r = residuef.get(n)
                r.set_residue_index(resnum)
                r.set_residue_type(res_name)
                n = n.add_child(atom_name, RMF.REPRESENTATION)
                a = atomf.get(n)
                a.set_element(12)
                p = particlef.get(n)
                p.set_mass(12.)
                p.set_radius(1.)
                p.set_coordinates(RMF.Vector3(1,2,3))
            add_residue(n, 'HET: N  ', 1, 'PCA')
            add_residue(n, 'C', 2, 'GLY')

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            # Two atoms in two residues should have been added
            state, = structures[0].child_models()
            self.assertEqual(len(state.residues), 2)
            self.assertEqual(len(state.atoms), 2)

            a1, a2 = state.atoms
            self.assertEqual(a1.name, 'N')
            self.assertEqual(a2.name, 'C')

    def test_alternatives(self):
        """Test open_rmf handling of RMF alternatives"""
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
            b = pf.get(g)
            b.set_radius(4)
            b.set_coordinates(RMF.Vector3(4.,5.,6.))
            a.add_alternative(root, RMF.GAUSSIAN_PARTICLE)

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            root = structures[0].rmf_hierarchy
            self.assertEqual(root.name, 'root')
            # All alternatives should be children of the root
            self.assertEqual([c.name for c in root.children],
                             ['topp1', 'topp2', 'topg1'])


if __name__ == '__main__':
    unittest.main()
