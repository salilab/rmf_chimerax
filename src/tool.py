# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.tools import ToolInstance
from chimerax.core.objects import Objects
from chimerax.atomic import Atoms, Bonds, Pseudobonds, Atom, Bond
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5 import QtWidgets


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

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.name


class _RMFFeaturesModel(QAbstractItemModel):
    """Map a list of RMF features into a QTreeView"""
    def __init__(self, rmf_features):
        super().__init__()
        self.rmf_features = rmf_features

    def columnCount(self, parent):
        # We always have just a single column (the node's name)
        return 1

    def rowCount(self, parent):
        if not parent.isValid():
            # the hidden top level owns all features
            return len(self.rmf_features)
        else:
            return 0

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.createIndex(row, column, self.rmf_features[row])

    def parent(self, index):
        # Only one level so always return the hidden top level
        return QModelIndex()

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

    def _fill_ui(self, *args):
        self.rmf_models = [m for m in self.session.models.list()
                           if hasattr(m, 'rmf_hierarchy')]

        self.model_list.clear()
        self.model_list.addItems("%s; %s" % (m.name, m.id_string)
                                 for m in self.rmf_models)

        self._fill_model_stack()

    def model_list_change(self, i):
        self.model_stack.setCurrentIndex(i)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage('side')

        combo_and_label = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("RMF model")
        combo_and_label.addWidget(label)
        self.model_list = QtWidgets.QComboBox()
        self.model_list.currentIndexChanged.connect(self.model_list_change)
        combo_and_label.addWidget(self.model_list, stretch=4)
        layout.addLayout(combo_and_label)

        self.model_stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.model_stack)

    def _fill_model_stack(self):
        self.model_stack.blockSignals(True)
        for i in range(self.model_stack.count()):
            self.model_stack.removeWidget(self.model_stack.widget(0))
        for m in self.rmf_models:
            self.model_stack.addWidget(self._build_ui_rmf_model(m))
        self.model_stack.blockSignals(False)

    def _build_ui_rmf_model(self, m):
        top = QtWidgets.QSplitter(Qt.Vertical)

        pane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        pane.setLayout(layout)

        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        label = QtWidgets.QLabel("Features")
        layout.addWidget(label)

        tree = QtWidgets.QTreeView()
        tree.setAnimated(False)
        tree.setIndentation(20)
        tree.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        tree.setSortingEnabled(False)
        tree.setHeaderHidden(True)
        tree.setModel(_RMFFeaturesModel(m.rmf_features))
        tree.selectionModel().selectionChanged.connect(
            lambda sel, desel, tree=tree: self._select_feature(tree))
        layout.addWidget(tree)
        top.addWidget(pane)

        pane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        pane.setLayout(layout)

        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        label = QtWidgets.QLabel("Hierarchy")
        layout.addWidget(label)

        tree = QtWidgets.QTreeView()
        tree.setAnimated(False)
        tree.setIndentation(20)
        tree.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        tree.setSortingEnabled(False)
        tree.setHeaderHidden(True)

        tree_and_buttons = QtWidgets.QHBoxLayout()
        tree_and_buttons.setContentsMargins(0,0,0,0)
        tree_and_buttons.setSpacing(0)

        tree_and_buttons.addWidget(tree, stretch=1)

        buttons = QtWidgets.QVBoxLayout()
        buttons.setContentsMargins(0,0,0,0)
        buttons.setSpacing(0)
        select_button = QtWidgets.QPushButton("Select")
        select_button.clicked.connect(lambda chk, tree=tree:
                                      self._select_button_clicked(tree))
        buttons.addWidget(select_button)
        hide_button = QtWidgets.QPushButton("Hide")
        hide_button.clicked.connect(lambda chk, tree=tree:
                                    self._hide_button_clicked(tree))
        buttons.addWidget(hide_button)
        show_button = QtWidgets.QPushButton("Show")
        show_button.clicked.connect(lambda chk, tree=tree:
                                    self._show_button_clicked(tree))
        buttons.addWidget(show_button)
        view_button = QtWidgets.QPushButton("View")
        view_button.clicked.connect(lambda chk, tree=tree:
                                    self._view_button_clicked(tree))
        buttons.addWidget(view_button)
        tree_and_buttons.addLayout(buttons)
        layout.addLayout(tree_and_buttons, stretch=1)
        top.addWidget(pane)

        tree.setModel(_RMFHierarchyModel(m.rmf_hierarchy))
        return top

    def _get_selected_chimera_objects(self, tree):
        def _get_node_objects(node, objs):
            if node.chimera_obj:
                objs.append(node.chimera_obj)
            for child in node.children:
                _get_node_objects(child, objs)
        objs = []
        for ind in tree.selectedIndexes():
            _get_node_objects(ind.internalPointer(), objs)
        objects = Objects()
        objects.add_atoms(Atoms(x for x in objs if isinstance(x, Atom)))
        objects.add_bonds(Bonds(x for x in objs if isinstance(x, Bond)))
        return objects

    def _get_selected_features(self, tree):
        def get_selection():
            for f in tree.selectedIndexes():
                obj = f.internalPointer().chimera_obj
                if obj is not None:
                    yield obj
        objs = Objects()
        objs.add_pseudobonds(Pseudobonds(get_selection()))
        return objs

    def _select_button_clicked(self, tree):
        from chimerax.std_commands.select import select
        select(self.session, self._get_selected_chimera_objects(tree))

    def _show_button_clicked(self, tree):
        from chimerax.std_commands.show import show
        show(self.session, self._get_selected_chimera_objects(tree))

    def _hide_button_clicked(self, tree):
        from chimerax.std_commands.hide import hide
        hide(self.session, self._get_selected_chimera_objects(tree))

    def _view_button_clicked(self, tree):
        from chimerax.std_commands.view import view
        view(self.session, self._get_selected_chimera_objects(tree))

    def _select_feature(self, tree):
        from chimerax.std_commands.select import select
        select(self.session, self._get_selected_features(tree))
