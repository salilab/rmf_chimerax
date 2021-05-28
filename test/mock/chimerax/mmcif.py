def open_mmcif(session, path, file_name=None, auto_style=True,
               coordsets=False, atomic=True, max_models=None, log_info=True,
               extra_categories=(), combine_sym_atoms=True):
    from chimerax.atomic import AtomicStructure
    return [AtomicStructure(session, name="test model")], 'message'
