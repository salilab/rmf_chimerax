# vim: set expandtab shiftwidth=4 softtabstop=4:

import numpy
import os.path


def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    rl = _RMFLoader()
    r, structures = rl.load(path, session)

    status = ("Opened RMF file produced with %s, with %d frames"
              % (r.get_producer(), r.get_number_of_frames()))
    return structures, status


from chimerax.core.models import Model
from chimerax.atomic import Structure

class _RMFState(Structure):
    """Representation of structure corresponding to a single RMF state"""
    pass


class _RMFModel(Model):
    """Representation of the top level of an RMF model"""
    def __init__(self, session, filename):
        name = os.path.splitext(filename)[0]
        self._session = session
        self._unnamed_state = None
        super().__init__(name, session)

    def _add_state(self, name):
        """Create and return a new _RMFState"""
        s = _RMFState(self._session, name=name)
        self.add([s])
        return s

    def get_unnamed_state(self):
        """Get the 'unnamed' state, used for structure that isn't the
           child of an RMF State node."""
        if self._unnamed_state is None:
            self._unnamed_state = self._add_state('Unnamed state')
        return self._unnamed_state


class _RMFHierarchyInfo(object):
    """Track structural information encountered through the RMF hierarchy"""
    def __init__(self, top_level):
        self.top_level = top_level
        self._refframe = self._state = self._chain = None

    def _set_reference_frame(self, rf):
        """Set the current reference frame from an RMF ReferenceFrame node"""
        # todo: handle nested reference frames
        from scipy.spatial.transform import Rotation
        rot = Rotation.from_quat(rf.get_rotation())
        self._refframe = (rot, numpy.array(rf.get_translation()))

    def handle_node(self, node, loader):
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
            rhi._chain = loader.chainf.get(node)
        return rhi

    def get_state(self):
        """Get the current state"""
        if self._state:
            return self._state
        else:
            # If we're not under a State node, use the unnamed state
            return self.top_level.get_unnamed_state()

    def new_atom(self, p):
        """Create and return a new ChimeraX Atom for the given Particle node.
           Call add_atom() to complete adding the atom to the model."""
        state = self.get_state()
        atom = state.new_atom('C', 'C')
        atom.coord = p.get_coordinates()
        if self._refframe:
            rot, trans = self._refframe
            atom.coord = rot.apply(atom.coord) + trans
        atom.mass = p.get_mass()
        atom.radius = p.get_radius()
        atom.draw_mode = atom.SPHERE_STYLE
        return atom

    def new_bond(self, a1, a2):
        state = self.get_state()
        return state.new_bond(a1, a2)

    def add_atom(self, atom, rnum, rtype):
        state = self.get_state()
        if self._chain is None:
            chain_id = 'X'
        else:
            chain_id = self._chain.get_chain_id()
        # todo: handle atomic (multiple atoms in same residue)
        self._residue = state.new_residue(rtype, chain_id, rnum)
        self._residue.add_atom(atom)


class _RMFLoader(object):
    """Load information from an RMF file"""

    def __init__(self):
        pass

    def load(self, path, session):
        from . import RMF

        structures = []
        r = RMF.open_rmf_file_read_only(path)
        self.particlef = RMF.ParticleConstFactory(r)
        self.coloredf = RMF.ColoredConstFactory(r)
        self.chainf = RMF.ChainConstFactory(r)
        self.fragmentf = RMF.FragmentConstFactory(r)
        self.residuef = RMF.ResidueConstFactory(r)
        self.refframef = RMF.ReferenceFrameConstFactory(r)
        self.statef = RMF.StateConstFactory(r)
        self.bondf = RMF.BondConstFactory(r)
        self.rmf_index_to_atom = {}

        r.set_current_frame(RMF.FrameID(0))

        top_level = _RMFModel(session, path)
        rhi = _RMFHierarchyInfo(top_level)
        self._handle_node(r.get_root_node(), rhi)
        return r, [top_level]

    def _handle_node(self, node, rhi):
        # Get hierarchy-related info from this node (e.g. chain, state)
        rhi = rhi.handle_node(node, self)
        if self.particlef.get_is(node):
            p = self.particlef.get(node)
            atom = rhi.new_atom(p)
            self.rmf_index_to_atom[node.get_index()] = atom
            if self.coloredf.get_is(node):
                c = self.coloredf.get(node)
                # RMF colors are 0-1 and has no alpha; ChimeraX uses 0-255
                atom.color = [x * 255. for x in c.get_rgb_color()] + [255]
            rtype = 'ALA'
            if self.fragmentf.get_is(node):
                f = self.fragmentf.get(node)
                resinds = f.get_residue_indexes()
                rnum = resinds[len(resinds) // 2]
            elif self.residuef.get_is(node):
                r = self.residuef.get(node)
                rnum = r.get_residue_index()
                rtype = r.get_residue_type()
            else:
                rnum = 1  # Make up a residue number if we don't have one
            rhi.add_atom(atom, rnum, rtype)
        if self.bondf.get_is(node):
            self._add_bond(self.bondf.get(node), rhi)
        for child in node.get_children():
            self._handle_node(child, rhi)

    def _add_bond(self, bond, rhi):
        rmfatom0 = bond.get_bonded_0()
        rmfatom1 = bond.get_bonded_1()
        atom0 = self.rmf_index_to_atom[rmfatom0.get_index()]
        atom1 = self.rmf_index_to_atom[rmfatom1.get_index()]
        rhi.new_bond(atom0, atom1)
