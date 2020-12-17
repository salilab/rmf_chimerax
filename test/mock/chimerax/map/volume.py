from chimerax.core.models import Model


class _VolumeData(object):
    step = [0, 0, 0]

    def set_step(self, step):
        self.step = step


class Volume(Model):
    def set_display_style(self, s):
        pass

    def show(self):
        pass


def open_map(session, path, name=None, format=None, **kw):
    models = [Volume('test', session)]
    models[0].data = _VolumeData()
    return models, "message"
