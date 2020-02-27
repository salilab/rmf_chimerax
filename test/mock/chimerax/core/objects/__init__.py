class Objects:
    def __init__(self, atoms=None, bonds=None, pseudobonds=None, models=None):
        self._atoms = []
        self._bonds = []
        self._pseudobonds = []

    def add_atoms(self, atoms, bonds=False):
        self._atoms.append(atoms)

    def add_bonds(self, bonds):
        self._bonds.append(bonds)

    def add_pseudobonds(self, pseudobonds):
        self._pseudobonds.append(pseudobonds)
