import weakref


class Pseudobond(object):
    def __init__(self, atom1, atom2):
        self.atoms = (atom1, atom2)


class PseudobondGroup(object):
    def __init__(self):
        self.pseudobonds = []

    def new_pseudobond(self, atom1, atom2, cs_id=None):
        p = Pseudobond(atom1, atom2)
        self.pseudobonds.append(p)
        return p


class Bond(object):
    def __init__(self, atom1, atom2):
        self.atoms = (atom1, atom2)


class _Element:
    def __init__(self, name):
        self.name = name


class Atom(object):
    SPHERE_STYLE = 1

    def __init__(self, name, element, structure):
        self._structure = weakref.ref(structure)
        self.name = name
        self.element = _Element(element)

    @property
    def structure(self):
        return self._structure()

    @property
    def coord_index(self):
        return self.structure.atoms.index(self)


class Residue(object):
    def __init__(self, name, chain_id):
        pass

    def add_atom(self, atom):
        atom.structure.atoms.append(atom)

class _AtomList(list):
    by_chain = property(lambda self: [])

class Structure(object):
    def __init__(self, session, *, name='structure', auto_style=True,
                 log_info=True):
        self.was_deleted = False
        self._pbg = None
        self._drawings = []
        self.atoms = _AtomList()
        self.bonds = []
        self.residues = []
        self.parent = None
        self.id = (1,1)
        self.id_string = '1.1'
        self.coordset_ids = [1]

    def take_snapshot(self, session, flags):
        return {'mock snapshot': None}

    @staticmethod
    def restore_snapshot(session, data):
        s = Structure(session)
        s.set_state_from_snapshot(session, data)
        return s

    def set_state_from_snapshot(self, session, data):
        pass

    def add_coordset(self, id, coord):
        if id not in self.coordset_ids:
            self.coordset_ids.append(id)

    def apply_auto_styling(self, set_lighting = False, style=None):
        pass

    def new_atom(self, atom_name, element):
        return Atom(atom_name, element, self)

    def new_residue(self, residue_name, chain_id, pos, insert=None,
                    *, precedes=None):
        r = Residue(residue_name, chain_id)
        self.residues.append(r)
        return r

    def new_bond(self, atom1, atom2):
        b = Bond(atom1, atom2)
        self.bonds.append(b)
        return b

    def pseudobond_group(self, name, *, create_type='normal'):
        if self._pbg is None:
            self._pbg = PseudobondGroup()
        return self._pbg

    def add_drawing(self, drawing):
        self._drawings.append(drawing)

class AtomicStructure(Structure):
    pass


class AtomicShapeDrawing(object):
    def __init__(self, name):
        self.name = name
        self._shapes = []

    def add_shape(self, vertices, normals, triangles, color, description=None):
        self._shapes.append((vertices, normals, triangles, color, description))

class Atoms:
    def __init__(self, atom_pointers=None):
        self._atom_pointers = list(atom_pointers)

    @property
    def coord_indices(self):
        return [a.coord_index for a in self._atom_pointers]

    @property
    def structures(self):
        return [a.structure for a in self._atom_pointers]

    @property
    def single_structure(self):
        seen_structures = frozenset(a.structure for a in self._atom_pointers)
        return len(seen_structures) <= 1

class Bonds:
    def __init__(self, bond_pointers=None):
        self._bond_pointers = list(bond_pointers)

class Pseudobonds:
    def __init__(self, pseudobond_pointers=None):
        self._pseudobond_pointers = list(pseudobond_pointers)
