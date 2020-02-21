class Pseudobond(object):
    pass


class PseudobondGroup(object):
    def new_pseudobond(self, atom1, atom2, cs_id=None):
        return Pseudobond()


class Bond(object):
    def __init__(self, atom1, atom2):
        pass


class Atom(object):
    SPHERE_STYLE = 1

    def __init__(self, name, element, structure):
        self.structure = structure


class Residue(object):
    def __init__(self, name, chain_id):
        pass

    def add_atom(self, atom):
        pass


class Structure(object):
    def __init__(self, session, *, name='structure'):
        self._pbg = None
        self._drawings = []

    def new_atom(self, atom_name, element):
        return Atom(atom_name, element, self)

    def new_residue(self, residue_name, chain_id, pos, insert=None,
                    *, precedes=None):
        return Residue(residue_name, chain_id)

    def new_bond(self, atom1, atom2):
        return Bond(atom1, atom2)

    def pseudobond_group(self, name, *, create_type='normal'):
        if self._pbg is None:
            self._pbg = PseudobondGroup()
        return self._pbg

    def add_drawing(self, drawing):
        self._drawings.append(drawing)


class AtomicShapeDrawing(object):
    def __init__(self, name):
        self.name = name
        self._shapes = []

    def add_shape(self, vertices, normals, triangles, color, description=None):
        self._shapes.append((vertices, normals, triangles, color, description))
