class Model(object):
    def __init__(self, name, session):
        self.name = name
        self.id_string = '1'
        self.session = session
        self._child_models = []

    def add(self, models):
        self._child_models.extend(models)

    def child_models(self):
        return self._child_models

ADD_MODELS = "add models"
REMOVE_MODELS = "remove models"
