import weakref
import sys
import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtWidgets import QTreeView, QPushButton

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

def make_provenance(name, index):
    n = MockRMFNode(name, index)
    return src.io._RMFProvenance(n)


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

    def test_rmf_provenance_model(self):
        """Test RMFProvenanceModel class"""
        f1 = make_provenance("f1", 1)
        f2 = make_provenance("f2", 2)
        child = make_provenance("child", 3)
        f1.previous = child
        child.next = weakref.proxy(f1)
        provs = [f1, f2]

        m = src.tool._RMFProvenanceModel(provs)
        top = QModelIndex()
        self.assertEqual(m.columnCount(None), 1)

        self.assertEqual(m.rowCount(top), 2)
        f1_ind = m.createIndex(0,0,f1)
        child_ind = m.createIndex(0,0,child)
        self.assertEqual(m.columnCount(f1_ind), 1)

        # Test indices
        self.assertEqual(m.index(0,0,top).internalPointer().name, 'f1')
        self.assertEqual(m.index(1,0,top).internalPointer().name, 'f2')
        self.assertFalse(m.index(2,0,top).isValid())
        self.assertEqual(m.index(0,0,f1_ind).internalPointer().name, 'child')
        # No parents for top level
        self.assertFalse(m.parent(top).isValid())
        self.assertFalse(m.parent(f1_ind).isValid())
        self.assertEqual(m.parent(child_ind).internalPointer().name, 'f1')
        self.assertEqual(m.data(f1_ind, Qt.DisplayRole), "f1")
        self.assertIsNone(m.data(f1_ind, Qt.SizeHintRole))

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_rmf_viewer(self):
        """Test creation of RMFViewer tool"""
        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = None
        m1.rmf_features = []
        m1.rmf_provenance = []
        m2 = Model(mock_session, 'test')
        mock_session.models.add((m1, m2))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        # Test update on model creation
        m3 = Model(mock_session, 'test')
        m3.rmf_hierarchy = None
        m3.rmf_features = []
        m3.rmf_provenance = []
        mock_session.models.add((m3,))

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
                    self.assertIsInstance(w.model(),
                            src.tool._RMFHierarchyModel)
                    return w
            raise ValueError("could not find tree")
        def get_buttons(stack):
            for w in stack.widget(1).children():
                if isinstance(w, QPushButton):
                    yield w
        root = make_node("root", 0)
        child1 = make_node("child1", 1)
        child1.chimera_obj = 'test object'
        child2 = make_node("child2", 2)
        grandchild = make_node("grandchild", 3)
        child2.add_children([grandchild])
        root.add_children((child1, child2))

        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = root

        m1.rmf_features = [make_node("f1", 4), make_node("f2", 5)]
        m1.rmf_provenance = []
        mock_session.models.add((m1,))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        tree1 = get_first_tree(r.model_stack.widget(0))
        buttons = list(get_buttons(r.model_stack.widget(0)))
        # Show, View, Hide, Select
        self.assertEqual(len(buttons), 4)
        # Call "clicked" methods directly
        r._select_button_clicked(tree1)
        tree1.selectAll()
        r._show_button_clicked(tree1)
        r._hide_button_clicked(tree1)
        r._view_button_clicked(tree1)
        # Call indirectly via clicking each button
        for b in buttons:
            b.click()

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_feature_selected(self):
        """Test selecting features"""
        def get_first_tree(stack):
            for w in stack.widget(0).children():
                if isinstance(w, QTreeView):
                    self.assertIsInstance(w.model(),
                            src.tool._RMFFeaturesModel)
                    return w
            raise ValueError("could not find tree")
        root = make_node("root", 0)
        mock_session = make_session()
        m1 = Model(mock_session, 'test')
        m1.rmf_hierarchy = root
        m1.rmf_features = [make_node("f1", 4), make_node("f2", 5)]
        m1.rmf_features[0].chimera_obj = 'test object'
        m1.rmf_provenance = []
        mock_session.models.add((m1,))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        tree1 = get_first_tree(r.model_stack.widget(0))
        r._select_feature(tree1)
        tree1.selectAll()

    @unittest.skipIf(utils.no_gui, "Cannot test without GUI")
    def test_load_provenance(self):
        """Test loading provenance"""
        def get_first_tree(stack):
            for w in stack.widget(2).children():
                if isinstance(w, QTreeView):
                    self.assertIsInstance(w.model(),
                            src.tool._RMFProvenanceModel)
                    return w
            raise ValueError("could not find tree")
        def get_buttons(stack):
            for w in stack.widget(2).children():
                if isinstance(w, QPushButton):
                    yield w
        root = make_node("root", 0)
        mock_session = make_session()
        m1 = src.io._RMFModel(mock_session, 'test')
        m1.rmf_hierarchy = root
        m1.rmf_features = []
        m1.rmf_provenance = [make_provenance("f1", 4), make_provenance("f2", 5)]
        mock_session.models.add((m1,))
        r = src.tool.RMFViewer(mock_session, "RMF Viewer")
        tree1 = get_first_tree(r.model_stack.widget(0))
        tree1.selectAll()
        r._load_button_clicked(tree1, m1)
        load_button, = list(get_buttons(r.model_stack.widget(0)))
        load_button.click()


if __name__ == '__main__':
    unittest.main()
