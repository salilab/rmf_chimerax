import os
import utils
import unittest

TOPDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
utils.set_search_paths(TOPDIR)

import src  # noqa: E402
import src.io  # noqa: E402
import src.tool  # noqa: E402


class Tests(unittest.TestCase):
    def test_get_class(self):
        """Test bundle get_class function"""
        self.assertIs(src.bundle_api.get_class("_RMFModel"), src.io._RMFModel)
        self.assertIs(src.bundle_api.get_class("RMFViewer"),
                      src.tool.RMFViewer)
        self.assertRaises(ValueError, src.bundle_api.get_class, "garbage")


if __name__ == '__main__':
    unittest.main()
