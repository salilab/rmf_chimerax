import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

from PyQt5.QtCore import QModelIndex, Qt

import src
import src.tool
import src.io


class MockRMFNode:
    def __init__(self, name, index):
        self.name, self.index = name, index
    def get_name(self): return self.name
    def get_index(self): return self.index

def make_node(name, index):
    n = MockRMFNode(name, index)
    return src.io._RMFHierarchyNode(n)


class Tests(unittest.TestCase):
    def test_rmf_hierarchy_model_none(self):
        """Test RMFHierarchyModel class with null hierarchy"""
        m = src.tool._RMFHierarchyModel(None)
        self.assertEqual(m.columnCount(None), 1)

        self.assertEqual(m.rowCount(QModelIndex()), 0)
        self.assertFalse(m.index(0,0,QModelIndex()).isValid())
        self.assertFalse(m.parent(QModelIndex()).isValid())
        self.assertEqual(m.headerData(0, Qt.Horizontal, Qt.DisplayRole),
                         "Node name")
        self.assertIsNone(m.data(QModelIndex(), Qt.DisplayRole))

    def test_rmf_hierarchy_model(self):
        """Test RMFHierarchyModel class"""
        root = make_node("root", 0)
        child1 = make_node("child1", 1)
        child2 = make_node("child2", 2)
        grandchild = make_node("grandchild", 3)
        child2.add_children([grandchild])
        root.add_children((child1, child2))

        m = src.tool._RMFHierarchyModel(root)
        self.assertEqual(m.columnCount(None), 1)
        # Top level has one child (RMF root)
        self.assertEqual(m.rowCount(QModelIndex()), 1)
        # RMF root has two children
        ind = m.createIndex(0,0,root)
        self.assertEqual(m.rowCount(ind), 2)
        # Test indices under RMF root
        self.assertEqual(m.index(0,0,ind).internalPointer().name, 'child1')
        self.assertEqual(m.index(1,0,ind).internalPointer().name, 'child2')
        self.assertFalse(m.index(2,0,ind).isValid())
        # Test top level index
        self.assertEqual(m.index(0,0,QModelIndex()).internalPointer().name,
                         'root')
        # Top level doesn't have a parent
        self.assertFalse(m.parent(QModelIndex()).isValid())
        childind = m.createIndex(0,0,child1)
        self.assertEqual(m.parent(childind).internalPointer().name, 'root')
        grandchildind = m.createIndex(0,0,grandchild)
        parentind = m.parent(grandchildind)
        self.assertEqual(parentind.internalPointer().name, 'child2')
        self.assertEqual(parentind.row(), 1)


if __name__ == '__main__':
    unittest.main()
