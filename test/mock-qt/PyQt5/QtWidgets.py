from PyQt5.QtCore import QModelIndex

class QApplication:
    def __init__(self, args):
        pass

class QWidget:
    def __init__(self):
        self._layout = None
    def setLayout(self, layout):
        self._layout = layout
    def layout(self):
        return self._layout
    def children(self):
        return self._layout.children()


class BoxLayout:
    def __init__(self):
        self._widgets = []
        self._layouts = []
    def children(self):
        for c in self._layouts + self._widgets:
            yield c
            if hasattr(c, 'children'):
                for child in c.children():
                    yield child
    def addWidget(self, w, stretch=0):
        self._widgets.append(w)
    def widget(self, i):
        return self._widgets[i]
    def layout(self, i):
        return self._layouts[i]
    def addLayout(self, l, stretch=0):
        self._layouts.append(l)
    def setContentsMargins(self, a,b,c,d):
        pass
    def setSpacing(self, spacing):
        pass

class QHBoxLayout(BoxLayout):
    pass

class QVBoxLayout(BoxLayout):
    pass

class QLabel:
    def __init__(self, txt):
        pass

class _Signal:
    def __init__(self):
        self._endpoint = None
    def connect(self, func):
        self._endpoint = func
    def _call(self, *args):
        if self._endpoint:
            self._endpoint(*args)

class QPushButton:
    def __init__(self, txt):
        self.clicked = _Signal()
    def click(self):
        self.clicked._call(False)

class QComboBox:
    def __init__(self):
        self.currentIndexChanged = _Signal()
    def clear(self):
        pass
    def addItems(self, items):
        pass

class QStackedWidget:
    def __init__(self):
        self._widgets = []
    def blockSignals(self, block):
        pass
    def count(self):
        return len(self._widgets)
    def addWidget(self, w):
        self._widgets.append(w)
    def removeWidget(self, w):
        self._widgets.remove(w)
    def widget(self, i):
        return self._widgets[i]

class _SelectionModel:
    def __init__(self):
        self.selectionChanged = _Signal()

class QTreeView:
    SingleSelection = 0
    ExtendedSelection = 1

    def __init__(self):
        self._selection_model = _SelectionModel()
        self._selinds = []
        self._model = None

    def selectionModel(self):
        return self._selection_model

    def setAnimated(self, flag):
        pass

    def setHeaderHidden(self, hidden):
        pass

    def setIndentation(self, indent):
        pass

    def setSortingEnabled(self, sorting):
        pass

    def blockSignals(self, block):
        pass

    def setModel(self, model):
        self._model = model

    def model(self):
        return self._model

    def setSelectionMode(self, mode):
        pass

    def selectAll(self):
        def add_selinds(parent):
            for row in range(self._model.rowCount(parent)):
                ind = self._model.index(row, 0, parent)
                self._selinds.append(ind)
                add_selinds(ind)
        self._selinds = []
        if self._model:
            add_selinds(QModelIndex())
        self._selection_model.selectionChanged._call(self._selinds, [])

    def selectedIndexes(self):
        return self._selinds

class QSplitter:
    def __init__(self, orientation, parent=None):
        self._widgets = []
    def addWidget(self, w, stretch=0):
        self._widgets.append(w)
    def widget(self, i):
        return self._widgets[i]
