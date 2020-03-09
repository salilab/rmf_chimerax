DEREGISTER = "deregister"

class TriggerSet:
    def __init__(self):
        self._tm = {}

    def add_handler(self, name, func):
        if name not in self._tm:
            self._tm[name] = []
        self._tm[name].append(func)

    def activate_trigger(self, name, data, absent_okay=False):
        for func in self._tm.get(name, []):
            func(name, data)
