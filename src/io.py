# vim: set expandtab shiftwidth=4 softtabstop=4:


def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    from . import RMF
    from chimerax.atomic import Structure

    structures = []

    r = RMF.open_rmf_file_read_only(path)
    # todo, actually read the file
    nframes = r.get_number_of_frames()
    r.set_current_frame(RMF.FrameID(0))

    pf = RMF.ParticleConstFactory(r)
    s = Structure(session)
    res = s.new_residue('ALA', 'A', 1)
    _handle_node(r.get_root_node(), pf, s, res)
    structures.append(s)

    status = ("Opened RMF file produced with %s, with %d frames"
              % (r.get_producer(), nframes))
    return structures, status


def _handle_node(node, pf, s, res):
    if pf.get_is(node):
        p = pf.get(node)
        atom = s.new_atom('C', 'C')
        atom.coord = p.get_coordinates()
        atom.mass = p.get_mass()
        atom.radius = p.get_radius()
        atom.draw_mode = atom.SPHERE_STYLE
        res.add_atom(atom)
    for child in node.get_children():
        _handle_node(child, pf, s, res)
