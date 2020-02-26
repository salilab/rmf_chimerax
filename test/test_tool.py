import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QTreeView

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

def make_feature(name, index):
    n = MockRMFNode(name, index)
    return src.io._RMFFeature(n)


class Tests(unittest.TestCase):
    def test_rmf_hierarchy_model_none(self):
        """Test RMFHierarchyModel class with null hierarchy"""
        m = src.tool._RMFHierarchyModel(None)
        self.assertEqual(m.columnCount(None), 1)

        self.assertEqual(m.rowCount(QModelIndex()), 0)
        self.assertFalse(m.index(0,0,QModelIndex()).isValid())
        self.assertFalse(m.parent(QModelIndex()).isValid())
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

    def test_rmf_features_model(self):
        """Test RMFFeaturesModel class"""
        features = [make_feature("f1", 1), make_feature("f2", 2)]

        m = src.tool._RMFFeaturesModel(features)
        top = QModelIndex()
        self.assertEqual(m.columnCount(None), 1)
        self.assertEqual(m.rowCount(top), 2)

        # Test indices
        self.assertEqual(m.index(0,0,top).internalPointer().name, 'f1')
        self.assertEqual(m.index(1,0,top).internalPointer().name, 'f2')
        self.assertFalse(m.index(2,0,top).isValid())
        # No parents
        self.assertFalse(m.parent(top).isValid())
        childind = m.createIndex(0,0,features[0])
        self.assertFalse(m.parent(childind).isValid())
        self.assertEqual(m.data(childind, Qt.DisplayRole), "f1")
        self.assertIsNone(m.data(childind, Qt.SizeHintRole))

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_rmf_viewer(self):
        """Test creation of RMFViewer tool"""
        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = None
        m1.rmf_features = []
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
        def get_first_tree(stack):
            for w in stack.widget(1).children():
                if isinstance(w, QTreeView):
                    return w
            raise ValueError("could not find tree")
        root = make_node("root", 0)
        child1 = make_node("child1", 1)
        child2 = make_node("child2", 2)
        grandchild = make_node("grandchild", 3)
        child2.add_children([grandchild])
        root.add_children((child1, child2))

        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = root

        m1.rmf_features = [make_node("f1", 4), make_node("f2", 5)]
        mock_session.models.add((m1,))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        tree1 = get_first_tree(r.model_stack.widget(0))
        r._select_button_clicked(tree1)
        tree1.selectAll()
        r._show_button_clicked(tree1)
        r._hide_button_clicked(tree1)
        r._view_button_clicked(tree1)


if __name__ == '__main__':
    unittest.main()
