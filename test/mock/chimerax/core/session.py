class _TriggerSet:
    def add_handler(self, name, func):
        pass

class _Models:
    def __init__(self):
        self._models = []
    def add(self, models):
        self._models.extend(models)
    def list(self):
        return self._models

class Session:
    def __init__(self, app_name, *, debug=False, silent=False, minimal=False):
        self.triggers = _TriggerSet()
        self.models = _Models()
