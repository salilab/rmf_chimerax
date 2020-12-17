from PyQt5.QtWidgets import QApplication, QWidget

app = QApplication([])


class _MockQWidget:
    def setLayout(self, layout):
        pass


class MainToolWindow:
    def __init__(self, tool_instance, **kw):
        self.ui_area = QWidget()

    def manage(self, placement, fixed_size=False, allowed_areas=None):
        pass
