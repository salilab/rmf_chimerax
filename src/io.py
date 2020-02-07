# vim: set expandtab shiftwidth=4 softtabstop=4:


def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    import RMF

    structures = []

    r = RMF.open_file_read_only(path)
    # todo, actually read the file

    status = "Opened RMF file"
    return structures, status
