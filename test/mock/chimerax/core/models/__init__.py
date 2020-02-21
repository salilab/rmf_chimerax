class Model(object):
    def __init__(self, name, session):
        self.session = session
        self._child_models = []

    def add(self, models):
        self._child_models.extend(models)

    def child_models(self):
        return self._child_models
