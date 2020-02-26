import weakref


class Pseudobond(object):
    pass


class PseudobondGroup(object):
    def new_pseudobond(self, atom1, atom2, cs_id=None):
        return Pseudobond()


class Bond(object):
    def __init__(self, atom1, atom2):
        pass


class _Element:
    def __init__(self, name):
        self.name = name


class Atom(object):
    SPHERE_STYLE = 1

    def __init__(self, name, element, structure):
        self.structure = weakref.proxy(structure)
        self.name = name
        self.element = _Element(element)


class Residue(object):
    def __init__(self, name, chain_id):
        pass

    def add_atom(self, atom):
        atom.structure.atoms.append(atom)


class Structure(object):
    def __init__(self, session, *, name='structure'):
        self._pbg = None
        self._drawings = []
        self.atoms = []
        self.residues = []

    def new_atom(self, atom_name, element):
        return Atom(atom_name, element, self)

    def new_residue(self, residue_name, chain_id, pos, insert=None,
                    *, precedes=None):
        r = Residue(residue_name, chain_id)
        self.residues.append(r)
        return r

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

class Atoms:
    def __init__(self, atom_pointers=None):
        pass

class Bonds:
    def __init__(self, bond_pointers=None):
        pass
