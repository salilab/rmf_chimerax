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


class MockLogger(object):
    def __init__(self):
        self.info_log = []
        self.warning_log = []

    def info(self, msg, is_html=False):
        self.info_log.append((msg, is_html))

    def warning(self, msg, is_html=False):
        self.warning_log.append((msg, is_html))


class MockRMFNode:
    def __init__(self, name, index):
        self.name, self.index = name, index
    def get_name(self): return self.name
    def get_index(self): return self.index


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

    def test_provenance(self):
        """Test open_rmf handling of RMF provenance"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()

            strucpf = RMF.StructureProvenanceFactory(r)
            samplepf = RMF.SampleProvenanceFactory(r)
            scriptpf = RMF.ScriptProvenanceFactory(r)
            softwarepf = RMF.SoftwareProvenanceFactory(r)

            n = rn.add_child("struc", RMF.PROVENANCE)
            p = strucpf.get(n)
            p.set_chain('A')
            p.set_residue_offset(42)
            p.set_filename('xyz')

            n = n.add_child("sample", RMF.PROVENANCE)
            p = samplepf.get(n)
            p.set_frames(100)
            p.set_iterations(10)
            p.set_method('Monte Carlo')
            p.set_replicas(8)

            n = n.add_child("script", RMF.PROVENANCE)
            p = scriptpf.get(n)
            p.set_filename('abc')

            n = rn.add_child("software", RMF.PROVENANCE)
            p = softwarepf.get(n)
            p.set_location('testurl')
            p.set_name('testsoftware')
            p.set_version('1.2.3')

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, p2 = structures[0].rmf_provenance
            self.assertEqual(p1.name, 'Chain A from xyz')
            self.assertEqual(p2.name,
                'Using software testsoftware version 1.2.3 from testurl')
            self.assertIsNone(p2.previous)
            prev = p1.previous
            self.assertEqual(prev.name,
                'Sampling using Monte Carlo making 100 frames')
            prev = prev.previous
            self.assertIn('Using script', prev.name)
            self.assertIsNone(prev.previous)

    def test_em_provenance(self):
        """Test open_rmf handling of RMF EM restraint provenance"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            imp_restraint_cat = r.get_category("IMP restraint")
            rsr_typek = r.get_key(imp_restraint_cat, "type", RMF.StringTag())

            imp_restraint_fn_cat = r.get_category("IMP restraint files")
            rsr_filenamek = r.get_key(imp_restraint_fn_cat, "filename",
                                      RMF.StringTag())

            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()

            represf = RMF.RepresentationFactory(r)
            particlef = RMF.ParticleFactory(r)

            pn = rn.add_child("p1", RMF.REPRESENTATION)
            p = particlef.get(pn)
            p.set_mass(12.)
            p.set_radius(1.)
            p.set_coordinates(RMF.Vector3(1,2,3))

            n = rn.add_child("r1", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "some other restraint")

            n = rn.add_child("nofname", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.isd.GaussianEMRestraint")

            n = rn.add_child("emr", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.isd.GaussianEMRestraint")
            n.set_value(rsr_filenamek, "abc")

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, = structures[0].rmf_provenance
            self.assertIsInstance(p1, src.io._RMFEMRestraintProvenance)

    def test_rmf_provenance_class(self):
        """Test _RMFProvenance class"""
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFProvenance(rmf_node)

        rmf_node = MockRMFNode("r2", 2)
        p2 = src.io._RMFProvenance(rmf_node)

        self.assertEqual(p.name, "r1")
        self.assertIsNone(p.previous)
        p.load(None, None)  # noop
        p.set_previous(p2)
        self.assertEqual(p.previous.name, "r2")
        self.assertEqual(p2.next.name, "r1")

    def test_rmf_structure_provenance(self):
        """Test _RMFStructureProvenance class"""
        class MockStructureProvenance:
            get_chain = lambda self: self.chain
            get_residue_offset = lambda self: self.residue_offset
            get_filename = lambda self: self.filename
        prov = MockStructureProvenance()
        prov.chain = 'A'
        prov.residue_offset = 0
        prov.filename = '/does/notexist'
        rmf_node = MockRMFNode("r1", 1)
        provenance_chains = {}
        p = src.io._RMFStructureProvenance(rmf_node, prov, provenance_chains)
        self.assertEqual(p.name, 'Chain A from notexist')
        self.assertEqual(p.chain, 'A')
        self.assertEqual(p.allchains, set('A'))

        prov2 = MockStructureProvenance()
        prov2.chain = 'B'
        prov2.residue_offset = 0
        prov2.filename = '/does/notexist'
        rmf_node2 = MockRMFNode("r2", 2)
        p2 = src.io._RMFStructureProvenance(rmf_node2, prov2, provenance_chains)
        self.assertEqual(p2.chain, 'B')
        self.assertEqual(p2.allchains, set('AB'))
        # allchains should have been updated for p too
        self.assertEqual(p.allchains, set('AB'))

        # Test with non-existent file
        mock_session = make_session()
        mock_session.logger = MockLogger()
        model = src.io._RMFModel(mock_session, 'fname')
        p.load(mock_session, model)
        self.assertIn('does not exist', mock_session.logger.warning_log[0][0])

        # File that does exist but unrecognized file format (not PDB, mmCIF)
        with utils.temporary_file(suffix='.dcd') as fname:
            p.filename = fname
            mock_session = make_session()
            mock_session.logger = MockLogger()
            model = src.io._RMFModel(mock_session, 'fname')
            p.load(mock_session, model)
            self.assertIn('file format not recognized',
                          mock_session.logger.warning_log[0][0])

        # PDB file
        with utils.temporary_file(suffix='.pdb') as fname:
            with open(fname, 'w') as fh:
                fh.write("""EXPDTA    THEORETICAL MODEL
ATOM      1  N   CYS     1       0.000   0.000   0.000  0.00999.99           N
ATOM      2  CA  CYS     1       1.453   0.000   0.000  0.00999.99           C
END
""")
            p.filename = fname
            mock_session = make_session()
            mock_session.logger = MockLogger()
            model = src.io._RMFModel(mock_session, 'fname')
            p.load(mock_session, model)
            provmodel, = model.child_models()
            self.assertEqual(provmodel.name, 'Provenance')
            self.assertEqual(len(provmodel.child_models()), 1)
            # Should be a noop to try to read it again
            p.load(mock_session, model)
            self.assertEqual(len(provmodel.child_models()), 1)

    def test_rmf_em_restraint_provenance(self):
        """Test _RMFEMRestraintProvenance class"""
        rmf_node = MockRMFNode("r1", 1)

        # Test with non-existent GMM file
        p = src.io._RMFEMRestraintProvenance(rmf_node, '/does/notexist')
        self.assertEqual(p.name, 'EM map from notexist')
        self.assertIsNone(p.mrc_filename)
        p.load(None, None)  # noop

        # Test with GMM file containing no metadata
        with utils.temporary_file(suffix='.gmm') as fname:
            with open(fname, 'w') as fh:
                pass
            p = src.io._RMFEMRestraintProvenance(rmf_node, fname)
            self.assertIsNone(p.mrc_filename)

        # Test with GMM file containing valid metadata
        with utils.temporary_directory() as tmpdir:
            gmm = os.path.join(tmpdir, 'test.gmm')
            mrc = os.path.join(tmpdir, 'test.mrc2')
            with open(gmm, 'w') as fh:
                fh.write("""# Created by create_gmm.py
# data_fn: test.mrc2
# ncenters: 50
""")
            with open(mrc, 'w') as fh:
                pass
            p = src.io._RMFEMRestraintProvenance(rmf_node, gmm)
            self.assertEqual(p.mrc_filename, mrc)
            self.assertEqual(p.name,
                'EM map from test.gmm (derived from test.mrc2)')
            mock_session = make_session()
            mock_session.logger = MockLogger()
            model = src.io._RMFModel(mock_session, 'fname')
            # Should be a noop since mrc2 isn't a known map format
            p.load(mock_session, model)


if __name__ == '__main__':
    unittest.main()
