import weakref
from chimerax.core.models import ADD_MODELS, REMOVE_MODELS
from . import triggerset

class _Models:
    def __init__(self, session):
        self._models = []
        self._next_id = 1
        self._session = weakref.ref(session)
    def add(self, models):
        def models_and_children(ms):
            for m in ms:
                yield m
                if hasattr(m, '_child_models'):
                    for child in models_and_children(m._child_models):
                        yield child
        for m in models_and_children(models):
            m.id = (self._next_id, 1)
            self._models.append(m)
            self._next_id += 1
        s = self._session()
        s.triggers.activate_trigger(ADD_MODELS, models)
    def list(self):
        return [m for m in self._models if not m.was_deleted]

class Session:
    def __init__(self, app_name, *, debug=False, silent=False, minimal=False):
        self.triggers = triggerset.TriggerSet()
        self.models = _Models(self)
