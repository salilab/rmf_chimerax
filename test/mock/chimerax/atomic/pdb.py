def open_pdb(session, stream, file_name, *, auto_style=True, coordsets=False,
             atomic=True, max_models=None, log_info=True,
             combine_sym_atoms=True):
    from chimerax.atomic import AtomicStructure
    return [AtomicStructure(session, name="test model")], 'message'
