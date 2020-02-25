import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

from PyQt5.QtCore import QModelIndex, Qt

import src
import src.tool
import src.io
from utils import make_session
from chimerax.core.models import Model


class MockBundleInfo:
    pass


class MockToolInfo:
    def __init__(self, name):
        self.name = name


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
        self.assertFalse(m.parent(ind).isValid())
        self.assertFalse(m.parent(QModelIndex()).isValid())
        childind = m.createIndex(0,0,child1)
        self.assertEqual(m.parent(childind).internalPointer().name, 'root')
        grandchildind = m.createIndex(0,0,grandchild)
        parentind = m.parent(grandchildind)
        self.assertEqual(parentind.internalPointer().name, 'child2')
        self.assertEqual(parentind.row(), 1)
        self.assertEqual(m.data(childind, Qt.DisplayRole), "child1")
        self.assertIsNone(m.data(childind, Qt.SizeHintRole))

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_rmf_viewer(self):
        """Test creation of RMFViewer tool"""
        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = None
        m2 = Model(mock_session, 'test')
        mock_session.models.add((m1, m2))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_bundle_api_make_tool(self):
        """Test open of tool via BundleAPI"""
        bundle_api = src.bundle_api
        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        mock_session.models.add((m1,))
        bi = MockBundleInfo()
        ti = MockToolInfo("RMF Viewer")
        bundle_api.start_tool(mock_session, bi, ti)

        ti = MockToolInfo("Bad tool")
        self.assertRaises(ValueError, bundle_api.start_tool,
                          mock_session, bi, ti)

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_button_clicks(self):
        """Test clicking on select/show/hide buttons"""
        root = make_node("root", 0)
        child1 = make_node("child1", 1)
        child2 = make_node("child2", 2)
        grandchild = make_node("grandchild", 3)
        child2.add_children([grandchild])
        root.add_children((child1, child2))

        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = root
        mock_session.models.add((m1,))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        r._select_button_clicked()
        r.tree.selectAll()
        r._show_button_clicked()
        r._hide_button_clicked()
        r._view_button_clicked()


if __name__ == '__main__':
    unittest.main()
