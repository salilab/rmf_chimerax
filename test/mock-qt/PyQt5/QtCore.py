class QModelIndex:
    def __init__(self):
        self._valid = False

    def isValid(self):
        return self._valid

    def row(self):
        return self._row

    def column(self):
        return self._column

    def internalPointer(self):
        return self._pointer

class Qt:
    Horizontal = 0
    DisplayRole = 1
    SizeHintRole = 2
    Vertical = 3


class QItemSelectionModel:
    Select = 2
    ClearAndSelect = 3

class QAbstractItemModel:
    def createIndex(self, row, column, pointer):
        ind = QModelIndex()
        ind._valid = True
        ind._row, ind._column, ind._pointer = row, column, pointer
        return ind

    def hasIndex(self, row, column, parent):
        ncol = self.columnCount(parent)
        nrow = self.rowCount(parent)
        return column < ncol and row < nrow

    def beginResetModel(self):
        pass

    def endResetModel(self):
        pass
