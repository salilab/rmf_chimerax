# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.tools import ToolInstance
from chimerax.core.objects import Objects
from chimerax.atomic import Atoms
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt


class _RMFHierarchyModel(QAbstractItemModel):
    """Map an RMF hierarchy into a QTreeView"""
    def __init__(self, rmf_hierarchy):
        super().__init__()
        self.rmf_hierarchy = rmf_hierarchy

    def columnCount(self, parent):
        # We always have just a single column (the node's name)
        return 1

    def rowCount(self, parent):
        if not parent.isValid():
            # the hidden top level has either one child
            # (the top of the RMF hierarchy) or no children (if the RMF
            # hierarchy is None)
            return 0 if self.rmf_hierarchy is None else 1
        else:
            parent_item = parent.internalPointer()
            return len(parent_item.children)

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            # top level only has one child (the top of the RMF hierarchy)
            # so return that
            if self.rmf_hierarchy is None:
                return QModelIndex()
            else:
                return self.createIndex(row, column, self.rmf_hierarchy)
        else:
            parent_item = parent.internalPointer()
            return self.createIndex(row, column, parent_item.children[row])

    def parent(self, index):
        """Get the parent of the given index (as another index)"""
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        if parent_item is None:
            # hidden top level node doesn't have an index
            return QModelIndex()
        else:
            parent_item = parent_item()
            if parent_item.parent is None:
                # top of the RMF hierarchy is always the 0th row of the
                # hidden top level node
                row = 0
            else:
                # otherwise, look up the parent in the grandparent's list of
                # children to determine its row
                row = parent_item.parent().children.index(parent_item)
            return self.createIndex(row, 0, parent_item)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return "Node name"

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.name


class RMFViewer(ToolInstance):
    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = False        # We do save/restore in sessions
    help = "help:user/tools/rmf.html"

    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)

        self._build_ui()
        from chimerax.core.models import ADD_MODELS, REMOVE_MODELS
        session.triggers.add_handler(ADD_MODELS, self._fill_ui)
        session.triggers.add_handler(REMOVE_MODELS, self._fill_ui)
        self._fill_ui()

    def _get_rmf_hierarchy(self):
        # todo: handle multiple RMF models, not just the first
        for m in self.session.models.list():
            if hasattr(m, 'rmf_hierarchy'):
                return m.rmf_hierarchy

    def _fill_ui(self, *args):
        self.tree.blockSignals(True)
        r = self._get_rmf_hierarchy()
        self.model = _RMFHierarchyModel(r)
        self.tree.setModel(self.model)
        self.tree.blockSignals(False)

    def _build_ui(self):
        from PyQt5 import QtWidgets
        layout = QtWidgets.QVBoxLayout()
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage('side')

        label = QtWidgets.QLabel("Hierarchy")
        layout.addWidget(label)

        self.tree = QtWidgets.QTreeView()
        self.tree.setAnimated(False)
        self.tree.setIndentation(20)
        self.tree.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        self.tree.setSortingEnabled(False)

        tree_and_buttons = QtWidgets.QHBoxLayout()
        tree_and_buttons.addWidget(self.tree)

        buttons = QtWidgets.QVBoxLayout()
        select_button = QtWidgets.QPushButton("Select")
        select_button.clicked.connect(self._select_button_clicked)
        buttons.addWidget(select_button)
        hide_button = QtWidgets.QPushButton("Hide")
        hide_button.clicked.connect(self._hide_button_clicked)
        buttons.addWidget(hide_button)
        show_button = QtWidgets.QPushButton("Show")
        show_button.clicked.connect(self._show_button_clicked)
        buttons.addWidget(show_button)
        tree_and_buttons.addLayout(buttons)

        layout.addLayout(tree_and_buttons)

    def _get_selected_chimera_objects(self):
        def _get_node_objects(node, atoms):
            if node.chimera_obj:
                atoms.append(node.chimera_obj)
            for child in node.children:
                _get_node_objects(child, atoms)
        atoms = []
        for ind in self.tree.selectedIndexes():
            _get_node_objects(ind.internalPointer(), atoms)
        objects = Objects()
        objects.add_atoms(Atoms(atoms))
        return objects

    def _select_button_clicked(self):
        from chimerax.std_commands.select import select
        select(self.session, self._get_selected_chimera_objects())

    def _show_button_clicked(self):
        from chimerax.std_commands.show import show
        show(self.session, self._get_selected_chimera_objects())

    def _hide_button_clicked(self):
        from chimerax.std_commands.hide import hide
        hide(self.session, self._get_selected_chimera_objects())
