import weakref

class Model(object):
    def __init__(self, name, session):
        self.was_deleted = False
        self.name = name
        self.id_string = '1'
        self.session = session
        self._child_models = []

    def delete(self):
        self.was_deleted = True

    def add(self, models):
        for m in models:
            self._child_models.append(m)
            m.parent = weakref.proxy(self)

    def child_models(self):
        return self._child_models

    def take_snapshot(self, session, flags):
        return {'mock snapshot': None}

    @staticmethod
    def restore_snapshot(session, data):
        s = Model(session)
        s.set_state_from_snapshot(session, data)
        return s

    def set_state_from_snapshot(self, session, data):
        pass

ADD_MODELS = "add models"
REMOVE_MODELS = "remove models"
