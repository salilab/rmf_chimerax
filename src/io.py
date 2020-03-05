# vim: set expandtab shiftwidth=4 softtabstop=4:

import numpy
import os.path
import sys
import weakref
import copy

def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    rl = _RMFLoader()
    r, structures = rl.load(path, session)

    numframes = r.get_number_of_frames()
    producer = r.get_producer()
    status = ("Opened RMF file%s with %d frame%s."
              % (" produced with %s," % producer if producer else "",
                 numframes, "" if numframes == 1 else "s"))
    if structures[0]._rmf_resolutions:
        status += (" Representation read at the following resolutions: %s."
                   % ", ".join("%.1f" % i for i in
                               sorted(structures[0]._rmf_resolutions)))
    if numframes > 1:
        status += (" Only the first frame was read; to read additional "
                   "frames, use the 'rmf readtraj' command.")
    if session.ui.is_gui:
        from chimerax.core.commands import run
        run(session, 'toolshed show "RMF Viewer"', log=False)
    return structures, status


from chimerax.core.models import Model
from chimerax.atomic import Structure, AtomicStructure, AtomicShapeDrawing

class _RMFState(AtomicStructure):
    """Representation of structure corresponding to a single RMF state"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._features = None
        # Assume the structure is atomic until we encounter coordinates without
        # atomic information
        self._atomic = True

    def _add_pseudobond(self, atoms):
        if self._features is None:
            self._features = self.pseudobond_group("Features")
        b = self._features.new_pseudobond(*atoms)
        b.halfbond = False
        return b

    def apply_auto_styling(self, *args, **kwargs):
        # Only apply auto styling for truly atomic structures
        if self._atomic:
            super().apply_auto_styling(*args, **kwargs)


class _RMFDrawing(Structure):
    """Representation of RMF geometry"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing = AtomicShapeDrawing('geometry')
        self.add_drawing(self._drawing)


class _RMFModel(Model):
    """Representation of the top level of an RMF model"""
    def __init__(self, session, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        self._unnamed_state = None
        self._drawing = None
        self._provenance = None
        self._provenance_map = {}
        self._rmf_resolutions = set()
        self._rmf_chains = []
        super().__init__(name, session)

    def _add_rmf_resolution(self, res):
        self._rmf_resolutions.add(res)

    def get_drawing(self):
        if self._drawing is None:
            self._drawing = _RMFDrawing(self.session, name="Geometry")
            self.add([self._drawing])
        return self._drawing

    def _has_provenance(self, filename):
        return filename in self._provenance_map

    def _add_provenance(self, filename, p):
        if self._provenance is None:
            self._provenance = Model('Provenance', self.session)
            self.add([self._provenance])
        self._provenance_map[filename] = p
        self._provenance.add([p])
        return self._provenance

    def _add_state(self, name):
        """Create and return a new _RMFState"""
        s = _RMFState(self.session, name=name)
        self.add([s])
        return s

    def _add_rmf_chain(self, chain, hierarchy):
        self._rmf_chains.append((chain.get_chain_id(), hierarchy))

    def get_unnamed_state(self):
        """Get the 'unnamed' state, used for structure that isn't the
           child of an RMF State node."""
        if self._unnamed_state is None:
            self._unnamed_state = self._add_state('Unnamed state')
        return self._unnamed_state

    def add_shape(self, vertices, normals, triangles, name):
        drawing = self.get_drawing()
        drawing._drawing.add_shape(vertices, normals, triangles,
                                   numpy.array([255,255,255,255]),
                                   description=name)


class _RMFHierarchyNode(object):
    """Represent a single RMF node.
       Note that features (restraints) are stored outside of this hierarchy,
       as _RMFFeature objects, as are provenance nodes."""
    __slots__ = ['name', 'rmf_index', 'children', 'parent', "__weakref__",
                 'chimera_obj']

    def __init__(self, rmf_node):
        self.name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.children = []
        self.chimera_obj = None
        self.parent = None

    def add_children(self, children):
        for child in children:
            self.children.append(child)
            # avoid circular reference
            child.parent = weakref.ref(self)


class _RMFFeature(object):
    """Represent a single feature in an RMF file."""
    __slots__ = ['name', 'rmf_index', 'chimera_obj']

    def __init__(self, rmf_node):
        self.name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.chimera_obj = None


class _RMFProvenance(object):
    """Represent some provenance of the RMF file."""

    def __init__(self, rmf_node):
        self._name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.chimera_obj = None
        self.previous = None
        self.next = None

    def set_previous(self, previous):
        """Add another _RMFProvenance node that represents the previous state
           of the system"""
        self.previous = previous
        previous.next = weakref.proxy(self)

    def load(self, session, model):
        """Override to load file(s) referenced by this object into the
           given session and model."""
        pass

    # Displayed name of this provenance (defaults to the name of the RMF node)
    name = property(lambda self: self._name)


def _atomic_model_reader(filename):
    """Get a ChimeraX function to read the given atomic model (PDB, mmCIF)"""
    if filename.endswith('.cif'):
        from chimerax.atomic.mmcif import open_mmcif
        return open_mmcif
    elif filename.endswith('.pdb'):
        from chimerax.atomic.pdb import open_pdb
        return open_pdb


class _RMFStructureProvenance(_RMFProvenance):
    """Represent a structure file (PDB, mmCIF) used as input for an RMF"""
    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: The chain ID used in the given file
        self.chain = prov.get_chain()
        #: Value to add to RMF residue numbers to get residue numbers
        #: in the file (usually zero)
        self.residue_offset = prov.get_residue_offset()
        #: Full path to PDB/mmCIF file
        self.filename = prov.get_filename()

    def load(self, session, model):
        # todo: read only the referenced chain(s) from each file
        if model._has_provenance(self.filename):
            return
        if not os.path.exists(self.filename):
            session.logger.warning("Not reading %s; does not exist"
                                   % self.filename)
        else:
            open_model = _atomic_model_reader(self.filename)
            if open_model:
                with open(self.filename) as fh:
                    models, msg = open_model(
                        session, fh, os.path.basename(self.filename),
                        auto_style=False, log_info=False)
                model._add_provenance(self.filename, models[0])
            else:
                session.logger.warning("Not reading %s; file format "
                                       "not recognized" % self.filename)

    def _get_name(self):
        return ("Chain %s from %s"
                % (self.chain, os.path.basename(self.filename)))
    name = property(_get_name)


class _RMFSampleProvenance(_RMFProvenance):
    """Information about how an RMF model was sampled"""
    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: Number of frames generated in the sampling
        self.frames = prov.get_frames()
        #: Number of scoring function iterations per frame
        self.iterations = prov.get_iterations()
        #: Sampling method used (e.g. Monte Carlo)
        self.method = prov.get_method()
        #: Number of replicas used in replica exchange sampling
        self.replicas = prov.get_replicas()

    def _get_name(self):
        return ("Sampling using %s making %d frames"
                % (self.method, self.frames))
    name = property(_get_name)


class _RMFScriptProvenance(_RMFProvenance):
    """Information about the script used to build an RMF model"""
    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: Full path to the script
        self.filename = prov.get_filename()

    def _get_name(self):
        return ("Using script %s" % self.filename)
    name = property(_get_name)


class _RMFSoftwareProvenance(_RMFProvenance):
    """Information about the software used to build an RMF model"""
    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: URL to obtain the software
        self.location = prov.get_location()
        #: Name of the software package
        self.software_name = prov.get_name()
        #: Version of the software used
        self.version = prov.get_version()

    def _get_name(self):
        return ("Using software %s version %s from %s" %
                (self.software_name, self.version, self.location))
    name = property(_get_name)


class _RMFEMRestraintProvenance(_RMFProvenance):
    """Information about an electron microscopy restraint"""
    def __init__(self, rmf_node, filename):
        super().__init__(rmf_node)
        #: Full path to GMM file
        self.filename = filename
        #: Full path to MRC file (if known)
        self.mrc_filename = self._parse_gmm(filename)

    def _parse_gmm(self, filename):
        """Extract metadata from the GMM file (to find the original MRC file)
           if available"""
        if not os.path.exists(filename):
            return
        with open(filename) as fh:
            for line in fh:
                if line.startswith('# data_fn: '):
                    relpath = line[11:].rstrip('\r\n')
                    return os.path.join(os.path.dirname(filename), relpath)

    def load(self, session, model):
        if (self.mrc_filename
            and not model._has_provenance(self.mrc_filename)):
            from chimerax.map.volume import open_map
            from chimerax.map.data import UnknownFileType
            try:
                maps, msg = open_map(session, self.mrc_filename)
            except UnknownFileType:
                return
            v = maps[0]
            v.set_display_style('image')
            v.show()
            model._add_provenance(self.mrc_filename, v)

    def _get_name(self):
        desc = "EM map from %s" % os.path.basename(self.filename)
        if self.mrc_filename:
            desc += " (derived from %s)" % os.path.basename(self.mrc_filename)
        return desc
    name = property(_get_name)


class _RMFHierarchyInfo(object):
    """Track structural information encountered through the RMF hierarchy"""
    def __init__(self, top_level):
        self.top_level = top_level
        self._refframe = self._state = self._chain = self._copy = None
        self._resolution = self._resnum = self._restype = None
        self._residue = None

    def _set_reference_frame(self, rf):
        """Set the current reference frame from an RMF ReferenceFrame node"""
        from scipy.spatial.transform import Rotation
        rot = rf.get_rotation()
        # RMF quaternions are scalar-first; scipy uses scalar-last
        rot = Rotation.from_quat((rot[1], rot[2], rot[3], rot[0]))
        tran = numpy.array(rf.get_translation())
        if self._refframe:
            # Compose with existing transformation
            oldrot, oldtran = self._refframe
            tran = oldrot.apply(tran) + oldtran
            rot = oldrot * rot
        self._refframe = (rot, tran)

    def handle_node(self, node, hierarchy, loader):
        """Extract structural information from the given RMF node.
           Return the _RMFHierarchyInfo object containing this information.
           This may be the current object, or a new one."""
        def copy_if_needed(x):
            # Make a copy if we need to so we don't mess with the information
            # used by parent nodes
            if x is self:
                return copy.copy(x)
            else:
                return x
        rhi = self
        if loader.statef.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._state = self.top_level._add_state(node.get_name())
        if loader.refframef.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._set_reference_frame(loader.refframef.get(node))
        if loader.chainf.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._chain = (node, loader.chainf.get(node))
            self.top_level._add_rmf_chain(rhi._chain[1], hierarchy)
        if loader.copyf.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._copy = loader.copyf.get(node).get_copy_index()
        if loader.resolutionf.get_is(node):
            rhi = copy_if_needed(rhi)
            n = loader.resolutionf.get(node)
            rhi._resolution = n.get_explicit_resolution()
            self.top_level._add_rmf_resolution(rhi._resolution)
        if loader.fragmentf.get_is(node):
            rhi = copy_if_needed(rhi)
            f = loader.fragmentf.get(node)
            resinds = f.get_residue_indexes()
            rhi._residue = None  # clear residue cache
            rhi._resnum = resinds[len(resinds) // 2]
            rhi._restype = 'ALA'  # Guess type
        if loader.residuef.get_is(node):
            rhi = copy_if_needed(rhi)
            r = loader.residuef.get(node)
            rhi._residue = None  # clear residue cache
            rhi._resnum = r.get_residue_index()
            rhi._restype = r.get_residue_type()
        return rhi

    def get_state(self):
        """Get the current state"""
        if self._state:
            return self._state
        else:
            # If we're not under a State node, use the unnamed state
            return self.top_level.get_unnamed_state()

    def get_residue(self):
        """Get the current residue"""
        if self._residue is None:  # Use cached residue if available
            state = self.get_state()
            if self._chain is None:
                chain_id = 'X'
            else:
                chain_id = self._chain[1].get_chain_id()
            if self._resnum is None:
                # If RMF provides no residue info, make it up
                self._residue = state.new_residue('ALA', chain_id, 1)
            else:
                self._residue = state.new_residue(self._restype, chain_id,
                                                  self._resnum)
            if self._chain:
                self._residue.rmf_name = self._chain[0].get_name()
            if self._copy is not None:
                self._residue.copy = self._copy
            if self._resolution is not None:
                self._residue.resolution = self._resolution
        return self._residue

    def new_atom(self, p, mass, name=None, element='C'):
        """Create and return a new ChimeraX Atom for the given Particle
           (and Atom, if applicable) node.
           Call add_atom() to complete adding the atom to the model."""
        state = self.get_state()
        if name is None:
            name = 'C'
            state._atomic = False
        atom = state.new_atom(name, element)
        atom.coord = p.get_coordinates()
        if self._refframe:
            rot, trans = self._refframe
            atom.coord = rot.apply(atom.coord) + trans
        atom.mass = mass
        atom.radius = p.get_radius()
        atom.draw_mode = atom.SPHERE_STYLE
        return atom

    def new_bond(self, a1, a2):
        state = a1.structure
        return state.new_bond(a1, a2)

    def new_feature(self, atoms):
        if len(atoms) == 2:
            state = atoms[0].structure
            return state._add_pseudobond(atoms)

    def new_segment(self, coords, name):
        # todo: don't rely on chimerax.bild (not public API)
        from chimerax.bild.bild import get_cylinder
        if len(coords) != 2:
            return
        a = numpy.array(coords[0])
        b = numpy.array(coords[1])
        # Skip zero-length lines
        if numpy.linalg.norm(a-b) < 1e-6:
            return
        vertices, normals, triangles = get_cylinder(1.0, a, b)
        self.top_level.add_shape(vertices, normals, triangles, name)

    def add_atom(self, atom):
        residue = self.get_residue()
        residue.add_atom(atom)


class _RMFLoader(object):
    """Load information from an RMF file"""

    def __init__(self):
        pass

    def load(self, path, session):
        if sys.platform == 'darwin':
            from .mac import RMF
        elif sys.platform == 'linux':
            from .linux import RMF
        else:
            from .windows import RMF

        self.GAUSSIAN_PARTICLE = RMF.GAUSSIAN_PARTICLE
        self.PARTICLE = RMF.PARTICLE
        self.PROVENANCE = RMF.PROVENANCE

        r = RMF.open_rmf_file_read_only(path)
        self.particlef = RMF.ParticleConstFactory(r)
        self.gparticlef = RMF.GaussianParticleConstFactory(r)
        self.ballf = RMF.BallConstFactory(r)
        self.strucprovf = RMF.StructureProvenanceConstFactory(r)
        self.sampleprovf = RMF.SampleProvenanceConstFactory(r)
        self.scriptprovf = RMF.ScriptProvenanceConstFactory(r)
        self.softwareprovf = RMF.SoftwareProvenanceConstFactory(r)
        self.coloredf = RMF.ColoredConstFactory(r)
        self.chainf = RMF.ChainConstFactory(r)
        self.fragmentf = RMF.FragmentConstFactory(r)
        self.residuef = RMF.ResidueConstFactory(r)
        self.refframef = RMF.ReferenceFrameConstFactory(r)
        self.statef = RMF.StateConstFactory(r)
        self.bondf = RMF.BondConstFactory(r)
        self.represf = RMF.RepresentationConstFactory(r)
        self.altf = RMF.AlternativesConstFactory(r)
        self.copyf = RMF.CopyConstFactory(r)
        self.resolutionf = RMF.ExplicitResolutionConstFactory(r)
        self.atomf = RMF.AtomConstFactory(r)
        self.segmentf = RMF.SegmentConstFactory(r)
        self.rmf_index_to_atom = {}

        imp_restraint_cat = r.get_category("IMP restraint")
        keys = dict((r.get_name(k), k)
                    for k in r.get_keys(imp_restraint_cat))
        self.rsr_typek = keys.get('type')

        imp_restraint_fn_cat = r.get_category("IMP restraint files")
        keys = dict((r.get_name(k), k)
                    for k in r.get_keys(imp_restraint_fn_cat))
        self.rsr_filenamek = keys.get('filename')

        r.set_current_frame(RMF.FrameID(0))

        top_level = _RMFModel(session, path)
        rhi = _RMFHierarchyInfo(top_level)
        top_level.rmf_filename = os.path.abspath(path)
        top_level.rmf_features = []
        top_level.rmf_provenance = []
        top_level.rmf_hierarchy, = self._handle_node(r.get_root_node(), rhi,
                                                     top_level.rmf_features,
                                                     top_level.rmf_provenance,
                                                     os.path.dirname(path))
        return r, [top_level]

    def _add_atom(self, node, p, mass, rhi):
        if self.atomf.get_is(node):
            ap = self.atomf.get(node)
            name = node.get_name()
            # ChimeraX names must not exceed 4 characters, so strip RMF/IMP
            # HET: prefix if present
            if name.startswith('HET:'):
                name = name[4:].strip()
            atom = rhi.new_atom(p, mass, name=name, element=ap.get_element())
        else:
            atom = rhi.new_atom(p, mass)
        self.rmf_index_to_atom[node.get_index()] = atom
        if self.coloredf.get_is(node):
            c = self.coloredf.get(node)
            # RMF colors are 0-1 and has no alpha; ChimeraX uses 0-255
            atom.color = [x * 255. for x in c.get_rgb_color()] + [255]
        rhi.add_atom(atom)
        return atom

    def _handle_provenance(self, node):
        if self.strucprovf.get_is(node):
            prov = _RMFStructureProvenance(node, self.strucprovf.get(node))
        elif self.sampleprovf.get_is(node):
            prov = _RMFSampleProvenance(node, self.sampleprovf.get(node))
        elif self.scriptprovf.get_is(node):
            prov = _RMFScriptProvenance(node, self.scriptprovf.get(node))
        elif self.softwareprovf.get_is(node):
            prov = _RMFSoftwareProvenance(node, self.softwareprovf.get(node))
        else:
            prov = _RMFProvenance(node)
        # Provenance nodes *should* only have at most one "child"
        for child in node.get_children():
            prov.set_previous(self._handle_provenance(child))
        return prov

    def _handle_feature_provenance(self, node, rmf_dir):
        # noop if these keys aren't in the file at all
        if self.rsr_typek is None or self.rsr_filenamek is None:
            return
        rsrtype = node.get_value(self.rsr_typek)
        if rsrtype == 'IMP.isd.GaussianEMRestraint':
            fname = node.get_value(self.rsr_filenamek)
            if fname:
                # path is relative to that of the RMF file
                fname = os.path.join(rmf_dir, fname)
                return _RMFEMRestraintProvenance(node, fname)

    def _handle_node(self, node, parent_rhi, features, provenance, rmf_dir):
        # Features are handled outside of the regular hierarchy
        if self.represf.get_is(node):
            feature = _RMFFeature(node)
            feature.chimera_obj = self._add_feature(
                                    self.represf.get(node), parent_rhi)
            features.append(feature)
            # Extract provenance from restraint if present
            p = self._handle_feature_provenance(node, rmf_dir)
            if p:
                provenance.append(p)
            return []

        # Provenance is handled outside of the regular hierarchy
        if node.get_type() == self.PROVENANCE:
            provenance.append(self._handle_provenance(node))
            return []

        rmf_nodes = [_RMFHierarchyNode(node)]
        # Get hierarchy-related info from this node (e.g. chain, state)
        rhi = parent_rhi.handle_node(node, rmf_nodes[0], self)
        if self.particlef.get_is(node):
            # todo: special handling for Gaussians; right now we assume that
            # every Gaussian is also a Particle, as 1) this is the case for
            # IMP-generated structures and 2) particlef.get_is() returns True
            # for Gaussians anyway (since it appears to only check for mass)
            p = self.particlef.get(node)
            atom = self._add_atom(node, p, p.get_mass(), rhi)
            rmf_nodes[0].chimera_obj = atom
        elif self.ballf.get_is(node):
            # balls have no mass
            atom = self._add_atom(node, self.ballf.get(node), 0., rhi)
            rmf_nodes[0].chimera_obj = atom
        if self.bondf.get_is(node):
            bond = self._add_bond(self.bondf.get(node), rhi)
            rmf_nodes[0].chimera_obj = bond
        if self.segmentf.get_is(node):
            self._add_segment(self.segmentf.get(node), node.get_name(), rhi)
        for child in node.get_children():
            rmf_nodes[0].add_children(self._handle_node(child, rhi, features,
                                                        provenance, rmf_dir))
        # Handle any alternatives (usually different resolutions)
        # Alternatives replace the current node - they are not children of
        # it - so use parent_rhi, not rhi.
        if self.altf.get_is(node):
            alt = self.altf.get(node)
            # The node itself should be the first alternative, so ignore that
            for p in alt.get_alternatives(self.PARTICLE)[1:]:
                rmf_nodes.extend(self._handle_node(p, parent_rhi, features,
                                                   provenance, rmf_dir))
            for gauss in alt.get_alternatives(self.GAUSSIAN_PARTICLE):
                rmf_nodes.extend(self._handle_node(gauss, parent_rhi, features,
                                                   provenance, rmf_dir))
        return rmf_nodes

    def _add_bond(self, bond, rhi):
        rmfatom0 = bond.get_bonded_0()
        rmfatom1 = bond.get_bonded_1()
        atom0 = self.rmf_index_to_atom[rmfatom0.get_index()]
        atom1 = self.rmf_index_to_atom[rmfatom1.get_index()]
        return rhi.new_bond(atom0, atom1)

    def _add_feature(self, feature, rhi):
        return rhi.new_feature([self.rmf_index_to_atom[x.get_index()]
                                for x in feature.get_representation()])

    def _add_segment(self, segment, name, rhi):
        rhi.new_segment(segment.get_coordinates_list(), name)
