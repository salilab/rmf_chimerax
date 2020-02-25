class QApplication:
    def __init__(self, args):
        pass

class QWidget:
    def setLayout(self, layout):
        pass


class QVBoxLayout:
    def addWidget(self, w):
        pass
    def addLayout(self, l):
        pass

class QHBoxLayout:
    def addWidget(self, w):
        pass
    def addLayout(self, l):
        pass

class QLabel:
    def __init__(self, txt):
        pass

class _Signal:
    def connect(self, func):
        pass

class QPushButton:
    def __init__(self, txt):
        self.clicked = _Signal()

class QTreeView:
    def setAnimated(self, flag):
        pass

    def setIndentation(self, indent):
        pass

    def setSortingEnabled(self, sorting):
        pass

    def blockSignals(self, block):
        pass

    def setModel(self, model):
        pass
