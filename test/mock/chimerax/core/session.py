import weakref
from chimerax.core.models import ADD_MODELS, REMOVE_MODELS

class _TriggerSet:
    def __init__(self):
        self._tm = {}

    def add_handler(self, name, func):
        if name not in self._tm:
            self._tm[name] = []
        self._tm[name].append(weakref.ref(func))

    def activate_trigger(self, name, data, absent_okay=False):
        for funcref in self._tm.get(name, []):
            func = funcref()
            if func is not None:
                func(name, data)

class _Models:
    def __init__(self, session):
        self._models = []
        self._session = weakref.ref(session)
    def add(self, models):
        self._models.extend(models)
        s = self._session()
        s.triggers.activate_trigger(ADD_MODELS, models)
    def list(self):
        return self._models

class Session:
    def __init__(self, app_name, *, debug=False, silent=False, minimal=False):
        self.triggers = _TriggerSet()
        self.models = _Models(self)
