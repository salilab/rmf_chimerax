# vim: set expandtab shiftwidth=4 softtabstop=4:

import numpy


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


class _RMFLoader(object):
    def __init__(self):
        pass

    def load(self, path, session):
        from . import RMF
        from chimerax.atomic import Structure

        structures = []
        r = RMF.open_rmf_file_read_only(path)
        self.particlef = RMF.ParticleConstFactory(r)
        self.coloredf = RMF.ColoredConstFactory(r)
        self.chainf = RMF.ChainConstFactory(r)
        self.fragmentf = RMF.FragmentConstFactory(r)
        self.residuef = RMF.ResidueConstFactory(r)
        self.refframef = RMF.ReferenceFrameConstFactory(r)

        # todo, actually read the file
        r.set_current_frame(RMF.FrameID(0))

        s = Structure(session)
        self._current_chain = None
        self._current_residue = None
        self._current_refframe = None
        self._handle_node(r.get_root_node(), s)
        return r, [s]

    def _add_atom(self, s, atom, rnum, rtype):
        if self._current_chain is None:
            chain_id = 'X'
        else:
            chain_id = self._current_chain.get_chain_id()
        self._current_residue = s.new_residue(rtype, chain_id, rnum)
        self._current_residue.add_atom(atom)

    def _set_reference_frame(self, rf):
        from scipy.spatial.transform import Rotation
        rot = Rotation.from_quat(rf.get_rotation())
        self._current_refframe = (rot, numpy.array(rf.get_translation()))

    def _handle_node(self, node, s):
        if self.refframef.get_is(node):
            self._set_reference_frame(self.refframef.get(node))
        if self.chainf.get_is(node):
            self._current_chain = self.chainf.get(node)
        if self.particlef.get_is(node):
            p = self.particlef.get(node)
            atom = s.new_atom('C', 'C')
            atom.coord = p.get_coordinates()
            if self._current_refframe:
                rot, trans = self._current_refframe
                atom.coord = rot.apply(atom.coord) + trans
            atom.mass = p.get_mass()
            atom.radius = p.get_radius()
            atom.draw_mode = atom.SPHERE_STYLE
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
            self._add_atom(s, atom, rnum, rtype)
        for child in node.get_children():
            self._handle_node(child, s)
