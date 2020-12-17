class CmdDesc(object):
    def __init__(self, required=(), optional=(), keyword=(),
                 postconditions=(), required_arguments=(),
                 non_keyword=(), hidden=(), url=None, synopsis=None):
        self.synopsis = synopsis


class IntArg:
    pass


class ModelArg:
    pass


def register(name, cmd_desc=(), function=None, *, logger=None, registry=None):
    pass


def run(session, text, *, log=True, downgrade_errors=False):
    pass
