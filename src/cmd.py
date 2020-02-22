# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.commands import CmdDesc
from chimerax.core.commands import IntArg, ModelArg


def _print_hierarchy(node, depth, level=0):
    yield "<li>%s" % node.name
    if node.children and (depth < 0 or depth > level):
        yield "<ul>"
        for child in node.children:
            for h in _print_hierarchy(child, depth, level+1):
                yield h
        yield "</ul>"
    yield "</li>"

def _hierarchy_html(model, depth):
    yield "<p>RMF hierarchy of model %s</p>" % model
    yield "<ul>"
    for x in _print_hierarchy(model.rmf_hierarchy, depth):
        yield x
    yield "</ul>"


def hierarchy(session, model, depth=-1):
    if not hasattr(model, 'rmf_hierarchy'):
        print("%s does not look like an RMF model" % model)
    else:
        session.logger.info("\n".join(_hierarchy_html(model, depth)),
                            is_html=True)


hierarchy_desc = CmdDesc(required=[("model", ModelArg)],
                         optional=[("depth", IntArg)])
