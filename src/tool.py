# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.tools import ToolInstance
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
            # the hidden top level has one child (the top of the RMF hierarchy)
            return 1
        else:
            parent_item = parent.internalPointer()
            return len(parent_item.children)

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            # top level only has one child (the top of the RMF hierarchy)
            # so return that
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

    def _get_rmf_hierarchy(self):
        # todo: handle multiple RMF models, not just the first
        for m in self.session.models.list():
            if hasattr(m, 'rmf_hierarchy'):
                return m.rmf_hierarchy

    def _build_ui(self):
        from PyQt5 import QtWidgets
        layout = QtWidgets.QVBoxLayout()
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage('side')

        label = QtWidgets.QLabel("Hierarchy")
        layout.addWidget(label)

        r = self._get_rmf_hierarchy()

        self.model = _RMFHierarchyModel(r)
        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.tree.setAnimated(False)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(False)

        tree_and_buttons = QtWidgets.QHBoxLayout()
        tree_and_buttons.addWidget(self.tree)

        buttons = QtWidgets.QVBoxLayout()
        select_button = QtWidgets.QPushButton("Select")
        buttons.addWidget(select_button)
        show_button = QtWidgets.QPushButton("Show")
        buttons.addWidget(show_button)
        hide_button = QtWidgets.QPushButton("Hide")
        buttons.addWidget(hide_button)
        tree_and_buttons.addLayout(buttons)

        layout.addLayout(tree_and_buttons)
