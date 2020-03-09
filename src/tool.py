# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.tools import ToolInstance
from chimerax.core.objects import Objects
from chimerax.atomic import Atoms, Bonds, Pseudobonds, Atom, Bond, Pseudobond
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtCore import QItemSelectionModel
from PyQt5 import QtWidgets


class _RMFHierarchyModel(QAbstractItemModel):
    """Map an RMF hierarchy into a QTreeView"""
    def __init__(self, rmf_hierarchy):
        super().__init__()
        self.rmf_hierarchy = rmf_hierarchy

    def index_for_node(self, rmf_node):
        """Return the index for a given node in the hierarchy"""
        parent = rmf_node.parent
        if parent is None:
            return self.index(0, 0, QModelIndex())
        else:
            parent = parent()
            row = parent.children.index(rmf_node)
            return self.createIndex(row, 0, rmf_node)

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
            parent_item = parent.internalPointer()
            return len(parent_item.children)

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            parent_list = self.rmf_features
        else:
            parent_list = parent.internalPointer().children
        return self.createIndex(row, column, parent_list[row])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent
        if parent_item is None:
            return QModelIndex()
        parent_item = parent_item()
        if parent_item.parent is None:
            row = self.rmf_features.index(parent_item)
        else:
            row = parent_item.parent().children.index(parent_item)
        return self.createIndex(row, 0, parent_item)

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.name


class _RMFProvenanceModel(QAbstractItemModel):
    """Map a list of RMF provenance into a QTreeView"""
    def __init__(self, rmf_provenance):
        super().__init__()
        self.rmf_provenance = rmf_provenance

    def columnCount(self, parent):
        # We always have just a single column (the node's name)
        return 1

    def rowCount(self, parent):
        if not parent.isValid():
            # the hidden top level owns all features
            return len(self.rmf_provenance)
        else:
            parent_item = parent.internalPointer()
            return 1 if parent_item.previous else 0

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            return self.createIndex(row, column, self.rmf_provenance[row])
        else:
            parent_item = parent.internalPointer()
            return self.createIndex(row, column, parent_item.previous)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.next
        if not parent_item:
             # hidden top level node doesn't have an index
            return QModelIndex()
        else:
            # provenance only has a single "previous", so row is always 0
            return self.createIndex(0, 0, parent_item)

    def data(self, index, role):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        item = index.internalPointer()
        return item.name


class RMFViewer(ToolInstance):
    SESSION_ENDURING = False    # Does this instance persist when session closes
    SESSION_SAVE = True         # We do save/restore in sessions
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

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'tool_name': self.tool_name,
                'selmodel': self.model_list.currentIndex()}
        return data

    @classmethod
    def restore_snapshot(cls, session, data):
        t = cls(session, data['tool_name'])
        t.model_list.setCurrentIndex(data['selmodel'])
        return t

    def _fill_ui(self, *args):
        self.rmf_models = [m for m in self.session.models.list()
                           if hasattr(m, 'rmf_hierarchy')]

        self.model_list.clear()
        self.model_list.addItems("%s; #%s" % (m.name, m.id_string)
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

        pane, hierarchy_tree = self._get_hierarchy_pane(m)
        top.addWidget(pane)

        pane = self._get_provenance_pane(m, hierarchy_tree)
        top.addWidget(pane)

        return top

    def _get_hierarchy_pane(self, m):
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
        tree.setModel(_RMFHierarchyModel(m.rmf_hierarchy))

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
        return pane, tree

    def _get_provenance_pane(self, m, hierarchy_tree):
        pane = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        pane.setLayout(layout)

        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        label = QtWidgets.QLabel("Provenance")
        layout.addWidget(label)

        tree = QtWidgets.QTreeView()
        tree.setAnimated(False)
        tree.setIndentation(20)
        tree.setSelectionMode(QtWidgets.QTreeView.ExtendedSelection)
        tree.setSortingEnabled(False)
        tree.setHeaderHidden(True)
        tree.setModel(_RMFProvenanceModel(m.rmf_provenance))
        tree.selectionModel().selectionChanged.connect(
            lambda sel, desel, tree=tree, hierarchy_tree=hierarchy_tree:
                self._select_provenance(tree, hierarchy_tree))

        tree_and_buttons = QtWidgets.QHBoxLayout()
        tree_and_buttons.setContentsMargins(0,0,0,0)
        tree_and_buttons.setSpacing(0)

        tree_and_buttons.addWidget(tree, stretch=1)

        buttons = QtWidgets.QVBoxLayout()
        buttons.setContentsMargins(0,0,0,0)
        buttons.setSpacing(0)
        load_button = QtWidgets.QPushButton("Load")
        load_button.clicked.connect(lambda chk, tree=tree, m=m:
                                    self._load_button_clicked(tree, m))
        buttons.addWidget(load_button)
        tree_and_buttons.addLayout(buttons)
        layout.addLayout(tree_and_buttons, stretch=1)
        return pane

    def _get_selected_chimera_objects(self, tree):
        def _get_node_objects(node, objs):
            o = node.chimera_obj
            if o:
                objs.append(o)
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
        def get_child_chimera_obj(feat):
            for child in feat.children:
                o = child.chimera_obj
                if o:
                    yield o
                for obj in get_child_chimera_obj(child):
                    yield obj
        def get_selection():
            for f in tree.selectedIndexes():
                feat = f.internalPointer()
                obj = feat.chimera_obj
                # Prefer to select pseudobonds (even from children)
                if (obj is not None
                    and (not isinstance(obj, Atoms) or not feat.children)):
                    yield obj
                else:
                    for obj in get_child_chimera_obj(feat):
                        yield obj
        s = list(get_selection())
        objs = Objects()
        objs.add_pseudobonds(Pseudobonds(x for x in s
                                         if isinstance(x, Pseudobond)))
        for x in s:
            if isinstance(x, Atoms):
                objs.add_atoms(x)
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

    def _select_provenance(self, tree, hierarchy_tree):
        mode = QItemSelectionModel.ClearAndSelect
        hierarchy_model = hierarchy_tree.model()
        hierarchy_selmodel = hierarchy_tree.selectionModel()
        for f in tree.selectedIndexes():
            obj = f.internalPointer()
            if obj.hierarchy_node:
                ind = hierarchy_model.index_for_node(obj.hierarchy_node)
                hierarchy_selmodel.setCurrentIndex(ind, mode)
                mode = QItemSelectionModel.Select

    def _load_button_clicked(self, tree, m):
        m._update_provenance_map()
        for f in tree.selectedIndexes():
            obj = f.internalPointer()
            obj.load(self.session, m)
