# vim: set expandtab shiftwidth=4 softtabstop=4:


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

        # todo, actually read the file
        r.set_current_frame(RMF.FrameID(0))

        s = Structure(session)
        res = s.new_residue('ALA', 'A', 1)
        self._handle_node(r.get_root_node(), s, res)
        return r, [s]

    def _handle_node(self, node, s, res):
        if self.particlef.get_is(node):
            p = self.particlef.get(node)
            atom = s.new_atom('C', 'C')
            atom.coord = p.get_coordinates()
            atom.mass = p.get_mass()
            atom.radius = p.get_radius()
            atom.draw_mode = atom.SPHERE_STYLE
            if self.coloredf.get_is(node):
                c = self.coloredf.get(node)
                # RMF colors are 0-1 and has no alpha; ChimeraX uses 0-255
                atom.color = [x * 255. for x in c.get_rgb_color()] + [255]
            res.add_atom(atom)
        for child in node.get_children():
            self._handle_node(child, s, res)
