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
from chimerax.atomic import Atoms
import chimerax.mmcif
import chimerax.pdb

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

    def test_bundle_api_open_old(self):
        """Test open file via BundleAPI (old mechanism)"""
        bundle_api = src.bundle_api
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = make_session()
        structures, status = bundle_api.open_file(mock_session, path, 'RMF')

    def test_bundle_api_open_new(self):
        """Test open file via BundleAPI (new mechanism)"""
        class MockOpenManager:
            pass
        mock_mgr = MockOpenManager()
        bundle_api = src.bundle_api
        path = os.path.join(INDIR, 'simple.rmf3')
        mock_session = make_session()
        oinfo = bundle_api.run_provider(mock_session, "RMF", mock_mgr)
        structures, status = oinfo.open(mock_session, path, path)

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

            n = rn.add_child("feat 1", RMF.FEATURE)
            f = rf.get(n)
            f.set_representation([n1.get_id(), n2.get_id()])

            childf = rf.get(n.add_child("child feat", RMF.FEATURE))
            childf.set_representation([n1.get_id(), n2.get_id()])

            f = rf.get(rn.add_child("feat 2", RMF.FEATURE))
            f.set_representation([n2.get_id(), n3.get_id()])

            # 3-particle feature (should be ignored)
            f = rf.get(rn.add_child("feat 3", RMF.FEATURE))
            f.set_representation([n1.get_id(), n2.get_id(), n3.get_id()])

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            # Three features (and one child) should have been added
            features = structures[0].rmf_features
            self.assertEqual(len(features), 3)
            self.assertIsInstance(features[0].chimera_obj, Pseudobond)
            self.assertIsInstance(features[1].chimera_obj, Pseudobond)
            self.assertIsInstance(features[2].chimera_obj, Atoms)
            child_feat, = features[0].children
            self.assertIsInstance(child_feat.chimera_obj, Pseudobond)

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

            n = rn.add_child("misc", RMF.PROVENANCE)

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, p2, p3 = structures[0].rmf_provenance
            self.assertEqual(p1.name, 'Chain A from xyz')
            self.assertEqual(p2.name,
                'Using software testsoftware version 1.2.3 from testurl')
            self.assertEqual(p3.name, 'misc')
            self.assertIsNone(p2.previous)
            prev = p1.previous
            self.assertEqual(prev.name,
                'Sampling using Monte Carlo making 100 frames')
            prev = prev.previous
            self.assertIn('Using script', prev.name)
            self.assertIsNone(prev.previous)
            self.assertIsInstance(p3, src.io._RMFProvenance)

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
            self.assertIsInstance(p1, src.io._RMFEMRestraintGMMProvenance)

    def test_xlms_provenance(self):
        """Test open_rmf handling of RMF XL-MS restraint provenance"""
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

            n = rn.add_child("nofname", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek,
                    "IMP.pmi.CrossLinkingMassSpectrometryRestraint")

            n = rn.add_child("emr", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek,
                    "IMP.pmi.CrossLinkingMassSpectrometryRestraint")
            n.set_value(rsr_filenamek, "abc")

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, = structures[0].rmf_provenance
            self.assertIsInstance(p1, src.io._RMFXLMSRestraintProvenance)
            self.assertEqual(p1.name, 'XL-MS data from abc')

    def test_saxs_provenance(self):
        """Test open_rmf handling of RMF SAXS restraint provenance"""
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

            n = rn.add_child("nofname", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.saxs.Restraint")

            n = rn.add_child("emr", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.saxs.Restraint")
            n.set_value(rsr_filenamek, "abc")

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, = structures[0].rmf_provenance
            self.assertIsInstance(p1, src.io._RMFSAXSRestraintProvenance)
            self.assertEqual(p1.name, 'SAXS profile from abc')

    def test_em2d_provenance(self):
        """Test open_rmf handling of RMF EM2D restraint provenance"""
        def make_rmf_file(fname):
            r = RMF.create_rmf_file(fname)
            imp_restraint_cat = r.get_category("IMP restraint")
            rsr_typek = r.get_key(imp_restraint_cat, "type", RMF.StringTag())
            rsr_pixelsizek = r.get_key(imp_restraint_cat, "pixel size",
                                        RMF.FloatTag())

            imp_restraint_fn_cat = r.get_category("IMP restraint files")
            rsr_imagefilesk = r.get_key(imp_restraint_fn_cat, "image files",
                                        RMF.StringsTag())

            r.add_frame("root", RMF.FRAME)
            rn = r.get_root_node()

            represf = RMF.RepresentationFactory(r)
            particlef = RMF.ParticleFactory(r)

            pn = rn.add_child("p1", RMF.REPRESENTATION)
            p = particlef.get(pn)
            p.set_mass(12.)
            p.set_radius(1.)
            p.set_coordinates(RMF.Vector3(1,2,3))

            n = rn.add_child("nofname", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.em2d.PCAFitRestraint")

            n = rn.add_child("emr", RMF.FEATURE)
            p = represf.get(n)
            p.set_representation([pn])
            n.set_value(rsr_typek, "IMP.em2d.PCAFitRestraint")
            n.set_value(rsr_pixelsizek, 1.0)
            n.set_value(rsr_imagefilesk, ["abc", "def"])

        with utils.temporary_file(suffix='.rmf') as fname:
            make_rmf_file(fname)
            mock_session = make_session()
            structures, status = src.io.open_rmf(mock_session, fname)
            p1, p2 = structures[0].rmf_provenance
            self.assertIsInstance(p1, src.io._RMFEM2DRestraintProvenance)
            self.assertEqual(p1.name, 'EM class average from abc')
            self.assertAlmostEqual(p1.pixel_size, 1.0, delta=1e-6)
            self.assertIsInstance(p2, src.io._RMFEM2DRestraintProvenance)
            self.assertEqual(p2.name, 'EM class average from def')
            self.assertAlmostEqual(p2.pixel_size, 1.0, delta=1e-6)

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

    def test_atomic_model_reader(self):
        """Test _atomic_model_reader"""
        f = src.io._atomic_model_reader("test.cif")
        self.assertIs(f, chimerax.mmcif.open_mmcif)
        f = src.io._atomic_model_reader("test.pdb")
        self.assertIs(f, chimerax.pdb.open_pdb)
        f = src.io._atomic_model_reader("test.dcd")
        self.assertIsNone(f)

    def test_prune_chains(self):
        """Test _prune_chains function"""
        class MockAtom:
            def __init__(self, cid, structure):
                self.structure, self.cid = structure, cid
                self.deleted = False
            def delete(self):
                self.deleted = True
        class AtomList:
            def __init__(self, atom):
                self.atoms = [atom]
            def delete(self):
                for a in self.atoms:
                    a.delete()
        class MockAtoms:
            def __init__(self):
                self._atoms = []
            def add(self, atoms):
                self._atoms.extend(atoms)
            @property
            def by_chain(self):
                # simple implementation, assumes only one atom in each chain
                return [(atom.structure, atom.cid, AtomList(atom))
                        for atom in self._atoms]
        class MockModel:
            def __init__(self):
                self.atoms = MockAtoms()
        m = MockModel()
        a1 = MockAtom('A', m)
        a2 = MockAtom('B', m)
        a3 = MockAtom('C', m)
        atoms = (a1, a2, a3)
        m.atoms.add(atoms)
        self.assertEqual([a.deleted for a in atoms], [False, False, False])
        # All chains kept
        src.io._prune_chains(m, frozenset('ABC'))
        self.assertEqual([a.deleted for a in atoms], [False, False, False])
        # Only some chains kept
        src.io._prune_chains(m, frozenset('CDE'))
        self.assertEqual([a.deleted for a in atoms], [True, True, False])

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

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFStructureProvenance.restore_snapshot(mock_session, s)
        self.assertIsInstance(newp, src.io._RMFStructureProvenance)

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
        p = src.io._RMFEMRestraintGMMProvenance(rmf_node, '/does/notexist')
        self.assertEqual(p.name, 'Gaussian Mixture Model from notexist')
        self.assertIsNone(p.previous)
        p.load(None, None)  # noop

        # Test with GMM file containing no metadata
        with utils.temporary_file(suffix='.gmm') as fname:
            with open(fname, 'w') as fh:
                pass
            p = src.io._RMFEMRestraintGMMProvenance(rmf_node, fname)
            self.assertIsNone(p.previous)

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
            p = src.io._RMFEMRestraintGMMProvenance(rmf_node, gmm)
            prev = p.previous
            self.assertEqual(prev.filename, mrc)
            self.assertEqual(p.name,
                'Gaussian Mixture Model from test.gmm')
            self.assertEqual(prev.name,
                'EM map from test.mrc2')
            mock_session = make_session()
            mock_session.logger = MockLogger()
            model = src.io._RMFModel(mock_session, 'fname')
            # Should be a noop since mrc2 isn't a known map format
            prev.load(mock_session, model)

    def test_rmf_em2d_restraint_provenance(self):
        """Test _RMFEM2DRestraintProvenance class"""
        rmf_node = MockRMFNode("r1", 1)

        with utils.temporary_directory() as tmpdir:
            pgm = os.path.join(tmpdir, 'test.pgm2')
            with open(pgm, 'w') as fh:
                pass
            p = src.io._RMFEM2DRestraintProvenance(rmf_node, pgm, 4.0)
            self.assertEqual(p.name,
                'EM class average from test.pgm2')
            mock_session = make_session()
            mock_session.logger = MockLogger()
            model = src.io._RMFModel(mock_session, 'fname')
            # Should be a noop since pgm2 isn't a known map format
            p.load(mock_session, model)

    def test_hierarchy_node_snapshot(self):
        """Test take/restore snapshot of RMFHierarchyNode"""
        rmf_node = MockRMFNode("r1", 1)
        n = src.io._RMFHierarchyNode(rmf_node)
        mock_session = make_session()
        s = n.take_snapshot(mock_session, None)
        newn = src.io._RMFHierarchyNode.restore_snapshot(mock_session, s)
        self.assertIsInstance(newn, src.io._RMFHierarchyNode)
        self.assertEqual(newn.name, "r1")
        self.assertEqual(newn.rmf_index, 1)
        self.assertEqual(newn.children, [])

    def test_feature_snapshot(self):
        """Test take/restore snapshot of RMFFeature"""
        rmf_node = MockRMFNode("r1", 1)
        n = src.io._RMFFeature(rmf_node)

        rmf_node = MockRMFNode("r2", 2)
        child = src.io._RMFFeature(rmf_node)
        n.add_child(child)

        mock_session = make_session()
        s = n.take_snapshot(mock_session, None)
        newn = src.io._RMFFeature.restore_snapshot(mock_session, s)
        self.assertIsInstance(newn, src.io._RMFFeature)
        self.assertEqual(newn.name, "r1")
        self.assertEqual(newn.rmf_index, 1)
        self.assertEqual(newn.children, [child])

    def test_rmf_sample_provenance(self):
        """Test _RMFSampleProvenance class"""
        class MockSampleProvenance:
            get_frames = lambda self: self.frames
            get_iterations = lambda self: self.iterations
            get_method = lambda self: self.method
            get_replicas = lambda self: self.replicas
        prov = MockSampleProvenance()
        prov.frames = 10
        prov.iterations = 10
        prov.method = 'Monte Carlo'
        prov.replicas = 8
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFSampleProvenance(rmf_node, prov)

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFSampleProvenance.restore_snapshot(mock_session, s)
        self.assertIsInstance(newp, src.io._RMFSampleProvenance)
        self.assertEqual(newp.frames, 10)
        self.assertEqual(newp.iterations, 10)
        self.assertEqual(newp.method, 'Monte Carlo')
        self.assertEqual(newp.replicas, 8)
        self.assertIsNone(newp.previous)

        rmf_node = MockRMFNode("r2", 2)
        previous = src.io._RMFProvenance(rmf_node)
        p.set_previous(previous)
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFSampleProvenance.restore_snapshot(mock_session, s)
        self.assertIs(newp.previous, previous)

    def test_rmf_script_provenance(self):
        """Test _RMFScriptProvenance class"""
        class MockScriptProvenance:
            get_filename = lambda self: self.filename
        prov = MockScriptProvenance()
        prov.filename = 'foo'
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFScriptProvenance(rmf_node, prov)

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFScriptProvenance.restore_snapshot(mock_session, s)
        self.assertIsInstance(newp, src.io._RMFScriptProvenance)
        self.assertEqual(newp.filename, 'foo')

    def test_rmf_software_provenance(self):
        """Test _RMFSoftwareProvenance class"""
        class MockSoftwareProvenance:
            get_location = lambda self: self.location
            get_name = lambda self: self.software_name
            get_version = lambda self: self.version
        prov = MockSoftwareProvenance()
        prov.location = 'foo'
        prov.software_name = 'bar'
        prov.version = 'baz'
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFSoftwareProvenance(rmf_node, prov)

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFSoftwareProvenance.restore_snapshot(mock_session, s)
        self.assertIsInstance(newp, src.io._RMFSoftwareProvenance)
        self.assertEqual(newp.location, 'foo')
        self.assertEqual(newp.software_name, 'bar')
        self.assertEqual(newp.version, 'baz')

    def test_rmf_em_gmm_provenance(self):
        """Test _RMFEMRestraintGMMProvenance class"""
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFEMRestraintGMMProvenance(rmf_node, 'foo')

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFEMRestraintGMMProvenance.restore_snapshot(
                            mock_session, s)
        self.assertIsInstance(newp, src.io._RMFEMRestraintGMMProvenance)
        self.assertEqual(newp.filename, 'foo')

    def test_rmf_em_mrc_provenance(self):
        """Test _RMFEMRestraintMRCProvenance class"""
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFEMRestraintMRCProvenance(rmf_node, 'foo')

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFEMRestraintMRCProvenance.restore_snapshot(
                            mock_session, s)
        self.assertIsInstance(newp, src.io._RMFEMRestraintMRCProvenance)
        self.assertEqual(newp.filename, 'foo')

    def test_rmf_xlms_provenance(self):
        """Test _RMFXLMSRestraintProvenance class"""
        rmf_node = MockRMFNode("r1", 1)
        p = src.io._RMFXLMSRestraintProvenance(rmf_node, 'foo')

        mock_session = make_session()
        s = p.take_snapshot(mock_session, None)
        newp = src.io._RMFXLMSRestraintProvenance.restore_snapshot(
                            mock_session, s)
        self.assertIsInstance(newp, src.io._RMFXLMSRestraintProvenance)
        self.assertEqual(newp.filename, 'foo')

    @unittest.skipIf(utils.no_gui, "Cannot test in real ChimeraX environment")
    def test_rmf_state_snapshot(self):
        """Test snapshot of RMFState class"""
        session = make_session()
        s = src.io._RMFState(session)
        d = s.take_snapshot(session, None)
        news = src.io._RMFState.restore_snapshot(session, d)
        self.assertIsInstance(news, src.io._RMFState)

    @unittest.skipIf(utils.no_gui, "Cannot test in real ChimeraX environment")
    def test_rmf_drawing_snapshot(self):
        """Test snapshot of RMFDrawing class"""
        session = make_session()
        s = src.io._RMFDrawing(session)
        d = s.take_snapshot(session, None)
        news = src.io._RMFDrawing.restore_snapshot(session, d)
        self.assertIsInstance(news, src.io._RMFDrawing)

    def test_rmf_model_snapshot(self):
        """Test snapshot of RMFModel class"""
        session = make_session()
        model1 = src.io._RMFModel(session, "test model")
        model1.rmf_features = []
        rmf_node = MockRMFNode("r1", 1)
        h1 = src.io._RMFHierarchyNode(rmf_node)
        model1.rmf_hierarchy = h1
        model2 = src.io._RMFModel(session, "deleted model")
        s = src.io._RMFModel(session, 'testfile')

        session.models.add([model1, model2, s])
        s.rmf_filename = 'foo'
        s.rmf_features = 'bar'
        s.rmf_provenance = 'baz'
        s.rmf_hierarchy = []
        s._provenance_map['testfname'] = model1
        s._provenance_map['test2'] = model2
        model2.delete()
        d = s.take_snapshot(session, None)
        news = src.io._RMFModel.restore_snapshot(session, d)
        self.assertIsInstance(news, src.io._RMFModel)
        self.assertEqual(news.rmf_filename, 'foo')
        self.assertEqual(news._provenance_map, {'testfname': model1.id})

    def test_save_snapshot_chimera_obj(self):
        """Test save_snapshot of Chimera objects"""
        self.assertIsNone(src.io._save_snapshot_chimera_obj(None))
        self.assertRaises(TypeError, src.io._save_snapshot_chimera_obj,
                          'non-chimera object')
        session = make_session()
        state = src.io._RMFState(session)
        state2 = src.io._RMFState(session)
        residue = state.new_residue('ALA', 'A', 1)
        atom1 = state.new_atom('C', 'C')
        residue.add_atom(atom1)
        atom2 = state.new_atom('N', 'N')
        residue.add_atom(atom2)

        st2_residue = state2.new_residue('ALA', 'A', 1)
        st2_atom1 = state2.new_atom('C', 'C')
        st2_residue.add_atom(st2_atom1)

        d = src.io._save_snapshot_chimera_obj(atom1)
        self.assertEqual(d['type'], 'Atom')

        # single structure
        atoms = Atoms((atom1, atom2))
        d = src.io._save_snapshot_chimera_obj(atoms)
        self.assertEqual(d['type'], 'Atoms')
        self.assertIn('single_structure', d)

        # multiple structures
        atoms = Atoms((atom1, st2_atom1))
        d = src.io._save_snapshot_chimera_obj(atoms)
        self.assertEqual(d['type'], 'Atoms')
        self.assertIn('structures', d)

        bond = state.new_bond(atom1, atom2)
        d = src.io._save_snapshot_chimera_obj(bond)
        self.assertEqual(d['type'], 'Bond')

        pbond = state._add_pseudobond((atom1, atom2))
        d = src.io._save_snapshot_chimera_obj(pbond)
        self.assertEqual(d['type'], 'Pseudobond')

    def test_load_snapshot_chimera_obj(self):
        """Test load_snapshot of Chimera objects"""
        session = make_session()
        self.assertIsNone(src.io._load_snapshot_chimera_obj(session, None, {}))
        self.assertRaises(TypeError, src.io._load_snapshot_chimera_obj,
                          session, {'type': 'garbage'}, {})
        state = src.io._RMFState(session)
        state2 = src.io._RMFState(session)
        residue = state.new_residue('ALA', 'A', 1)
        atom1 = state.new_atom('C', 'C')
        residue.add_atom(atom1)
        atom2 = state.new_atom('N', 'N')
        residue.add_atom(atom2)

        st2_residue = state2.new_residue('ALA', 'A', 1)
        st2_atom1 = state2.new_atom('C', 'C')
        st2_residue.add_atom(st2_atom1)

        bond = state.new_bond(atom1, atom2)
        d = src.io._save_snapshot_chimera_obj(bond)
        self.assertEqual(d['type'], 'Bond')

        pbond = state._add_pseudobond((atom1, atom2))
        d = src.io._save_snapshot_chimera_obj(pbond)
        self.assertEqual(d['type'], 'Pseudobond')

        model_by_id = {(1,1): state, (2,1): state2}
        data = {'type': 'Atoms',
                'single_structure': (1,1),
                'indices': [0, 1]}
        obj = src.io._load_snapshot_chimera_obj(session, data, model_by_id)
        self.assertIsInstance(obj, Atoms)

        data = {'type': 'Atoms',
                'structures': [(1,1), (2,1)],
                'indices': [0, 0]}
        obj = src.io._load_snapshot_chimera_obj(session, data, model_by_id)
        self.assertIsInstance(obj, Atoms)

        data = {'type': 'Atom',
                'structure': (1,1),
                'index': 0}
        obj = src.io._load_snapshot_chimera_obj(session, data, model_by_id)
        self.assertIs(obj, atom1)

        data = {'type': 'Bond',
                'structure': (1,1),
                'index': 0}
        obj = src.io._load_snapshot_chimera_obj(session, data, model_by_id)
        self.assertIs(obj, bond)

        data = {'type': 'Pseudobond',
                'structure': (1,1),
                'index': 0}
        obj = src.io._load_snapshot_chimera_obj(session, data, model_by_id)
        self.assertIs(obj, pbond)

    def test_restore_chimera_obj(self):
        """Test _restore_chimera_obj function"""
        from chimerax.core.triggerset import DEREGISTER
        session = make_session()
        model = src.io._RMFModel(session, "test model")
        model2 = src.io._RMFModel(session, "test model")
        state = model._add_state("state 0")
        session.models.add([model, model2])

        residue = state.new_residue('ALA', 'A', 1)
        atom1 = state.new_atom('C', 'C')
        residue.add_atom(atom1)
        atom2 = state.new_atom('N', 'N')
        residue.add_atom(atom2)

        rmf_node = MockRMFNode("r1", 1)
        f1 = src.io._RMFFeature(rmf_node)
        f1.chimera_obj = {'type': 'Atom', 'structure': state.id,
                          'index': 0}

        rmf_node = MockRMFNode("r2", 2)
        f2 = src.io._RMFFeature(rmf_node)
        f1.add_child(f2)
        model.rmf_features = [f1]
        model2.rmf_features = []

        rmf_node = MockRMFNode("r3", 3)
        h1 = src.io._RMFHierarchyNode(rmf_node)

        rmf_node = MockRMFNode("r4", 4)
        h2 = src.io._RMFHierarchyNode(rmf_node)
        h2.chimera_obj = {'type': 'Atom', 'structure': state.id,
                          'index': 1}
        h1.add_children([h2])
        model.rmf_hierarchy = h1

        rmf_node = MockRMFNode("r4", 4)
        h3 = src.io._RMFHierarchyNode(rmf_node)
        model2.rmf_hierarchy = h3

        model._provenance_map['testfname'] = model2.id
        ret = src.io._restore_chimera_obj(session, model)
        self.assertIs(model._provenance_map['testfname'], model2)
        self.assertIs(f1.chimera_obj, atom1)
        self.assertIs(h2.chimera_obj, atom2)
        self.assertEqual(ret, DEREGISTER)


if __name__ == '__main__':
    unittest.main()
