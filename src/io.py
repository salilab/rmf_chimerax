# vim: set expandtab shiftwidth=4 softtabstop=4:

import numpy
import os.path
import sys
import weakref


def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    rl = _RMFLoader()
    r, structures = rl.load(path, session)

    numframes = r.get_number_of_frames()
    producer = r.get_producer()
    status = ("Opened RMF file%s with %d frame%s"
              % (" produced with %s," % producer if producer else "",
                 numframes, "" if numframes == 1 else "s"))
    if session.ui.is_gui:
        from chimerax.core.commands import run
        run(session, 'toolshed show "RMF Viewer"', log=False)
    return structures, status


from chimerax.core.models import Model
from chimerax.atomic import Structure, AtomicShapeDrawing

class _RMFState(Structure):
    """Representation of structure corresponding to a single RMF state"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._features = None

    def _add_pseudobond(self, atoms):
        if self._features is None:
            self._features = self.pseudobond_group("Features")
        b = self._features.new_pseudobond(*atoms)
        b.halfbond = False


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
        self._rmf_chains = []
        super().__init__(name, session)

    def get_drawing(self):
        if self._drawing is None:
            self._drawing = _RMFDrawing(self.session, name="Geometry")
            self.add([self._drawing])
        return self._drawing

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
    """Represent a single RMF node"""
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


class _RMFHierarchyInfo(object):
    """Track structural information encountered through the RMF hierarchy"""
    def __init__(self, top_level):
        self.top_level = top_level
        self._refframe = self._state = self._chain = self._copy = None
        self._resolution = self._resnum = self._restype = None
        self._residue = None

    def _set_reference_frame(self, rf):
        """Set the current reference frame from an RMF ReferenceFrame node"""
        # todo: handle nested reference frames
        from scipy.spatial.transform import Rotation
        rot = Rotation.from_quat(rf.get_rotation())
        self._refframe = (rot, numpy.array(rf.get_translation()))

    def handle_node(self, node, hierarchy, loader):
        """Extract structural information from the given RMF node.
           Return the _RMFHierarchyInfo object containing this information.
           This may be the current object, or a new one."""
        def copy_if_needed(x):
            # Make a copy if we need to so we don't mess with the information
            # used by parent nodes
            if x is self:
                return x
            else:
                return copy.copy(x)
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

    def new_atom(self, p, mass, name='C', element='C'):
        """Create and return a new ChimeraX Atom for the given Particle
           (and Atom, if applicable) node.
           Call add_atom() to complete adding the atom to the model."""
        state = self.get_state()
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
        state = self.get_state()
        return state.new_bond(a1, a2)

    def new_feature(self, atoms):
        if len(atoms) == 2:
            state = atoms[0].structure
            state._add_pseudobond(atoms)

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

        structures = []
        r = RMF.open_rmf_file_read_only(path)
        self.particlef = RMF.ParticleConstFactory(r)
        self.gparticlef = RMF.GaussianParticleConstFactory(r)
        self.ballf = RMF.BallConstFactory(r)
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

        r.set_current_frame(RMF.FrameID(0))

        top_level = _RMFModel(session, path)
        rhi = _RMFHierarchyInfo(top_level)
        top_level.rmf_hierarchy, = self._handle_node(r.get_root_node(), rhi)
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

    def _handle_node(self, node, parent_rhi):
        rmf_nodes = [_RMFHierarchyNode(node)]
        # Get hierarchy-related info from this node (e.g. chain, state)
        rhi = parent_rhi.handle_node(node, rmf_nodes[0], self)
        if self.gparticlef.get_is(node):
            # todo: do something with Gaussians
            pass
        elif self.particlef.get_is(node):
            p = self.particlef.get(node)
            atom = self._add_atom(node, p, p.get_mass(), rhi)
            rmf_nodes[0].chimera_obj = atom
        elif self.ballf.get_is(node):
            # balls have no mass
            atom = self._add_atom(node, self.ballf.get(node), 0., rhi)
            rmf_nodes[0].chimera_obj = atom
        if self.bondf.get_is(node):
            self._add_bond(self.bondf.get(node), rhi)
        if self.represf.get_is(node):
            self._add_feature(self.represf.get(node), rhi)
        if self.segmentf.get_is(node):
            self._add_segment(self.segmentf.get(node), node.get_name(), rhi)
        for child in node.get_children():
            rmf_nodes[0].add_children(self._handle_node(child, rhi))
        # Handle any alternatives (usually different resolutions)
        # Alternatives replace the current node - they are not children of
        # it - so use parent_rhi, not rhi.
        if self.altf.get_is(node):
            alt = self.altf.get(node)
            # The node itself should be the first alternative, so ignore that
            for p in alt.get_alternatives(self.PARTICLE)[1:]:
                rmf_nodes.extend(self._handle_node(p, parent_rhi))
            for gauss in alt.get_alternatives(self.GAUSSIAN_PARTICLE):
                rmf_nodes.extend(self._handle_node(gauss, parent_rhi))
        return rmf_nodes

    def _add_bond(self, bond, rhi):
        rmfatom0 = bond.get_bonded_0()
        rmfatom1 = bond.get_bonded_1()
        atom0 = self.rmf_index_to_atom[rmfatom0.get_index()]
        atom1 = self.rmf_index_to_atom[rmfatom1.get_index()]
        rhi.new_bond(atom0, atom1)

    def _add_feature(self, feature, rhi):
        rhi.new_feature([self.rmf_index_to_atom[x.get_index()]
                         for x in feature.get_representation()])

    def _add_segment(self, segment, name, rhi):
        rhi.new_segment(segment.get_coordinates_list(), name)
