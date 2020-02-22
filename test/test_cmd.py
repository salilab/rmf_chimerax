import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src
import src.cmd
import src.io

class MockLogger(object):
    def __init__(self):
        self.info_log = []

    def info(self, msg, is_html=False):
        self.info_log.append((msg, is_html))


class MockSession(object):
    def __init__(self):
        self.logger = MockLogger()


class Tests(unittest.TestCase):
    def test_hierarchy_register(self):
        """Test register of rmf hierarchy command"""
        class MockCommandInfo:
            def __init__(self, name, synopsis):
                self.name, self.synopsis = name, synopsis
        bundle_api = src.bundle_api
        ci = MockCommandInfo("rmf hierarchy", "test synopsis")
        bundle_api.register_command(None, ci, None)

        ci = MockCommandInfo("bad command", "test synopsis")
        self.assertRaises(ValueError, bundle_api.register_command,
                          None, ci, None)

    def test_hierarchy_not_rmf(self):
        """Test hierarchy command on a model that is not an RMF"""
        mock_session = MockSession()
        src.cmd.hierarchy(mock_session, 'garbage model')
        self.assertEqual(mock_session.logger.info_log, [])

    def test_hierarchy(self):
        """Test hierarchy command"""
        class MockModel:
            pass
        class MockRMFNode:
            def __init__(self, name, index):
                self.name, self.index = name, index
            def get_name(self): return self.name
            def get_index(self): return self.index
        def make_node(name, index):
            n = MockRMFNode(name, index)
            return src.io._RMFHierarchyNode(n)

        root = make_node("root", 0)
        child1 = make_node("child1", 1)
        child2 = make_node("child2", 2)
        grandchild1 = make_node("grandchild1", 3)
        grandchild2 = make_node("grandchild2", 4)
        root.children.extend((child1, child2))
        child1.children.extend((grandchild1, grandchild2))
        test_model = MockModel()
        test_model.rmf_hierarchy = root
        mock_session = MockSession()
        src.cmd.hierarchy(mock_session, test_model)
        (log, is_html), = mock_session.logger.info_log
        def get_li_lines(l):
            return [line[4:] for line in l.split("\n")
                    if line.startswith('<li>')]
        self.assertTrue(is_html)
        # Default depth shows everything
        self.assertEqual(get_li_lines(log),
                         ['root', 'child1', 'grandchild1',
                          'grandchild2', 'child2'])

        src.cmd.hierarchy(mock_session, test_model, depth=1)
        log, is_html = mock_session.logger.info_log[-1]
        self.assertEqual(get_li_lines(log), ['root', 'child1', 'child2'])


if __name__ == '__main__':
    unittest.main()
