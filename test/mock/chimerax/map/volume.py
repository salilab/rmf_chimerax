from chimerax.core.models import Model

class Volume(Model):
    def set_display_style(self, s):
        pass
    def show(self):
        pass

def open_map(session, path, name = None, format = None, **kw):
    models = [Volume('test', session)]
    return models, "message"

