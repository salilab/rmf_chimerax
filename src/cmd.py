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


def _chains_html(model):
    from chimerax.core.logger import html_table_params
    def link_chain_id(cid):
        return('<a title="Select chain" href="cxcmd:select #%s/%s">%s</a>'
               % (model.id_string, cid, cid))
    body_template = """
    <tr>
      <td>%s</td>
      <td>%s</td>
    </tr>
"""
    body = "\n".join(body_template % (c[1].name, link_chain_id(c[0]))
                     for c in model._rmf_chains)
    return """
<table %s>
  <thead>
    <tr>
      <th colspan="2">Chains for %s</th>
    </tr>
    <tr>
      <th>RMF name</th>
      <th>Chain ID</th>
    </tr>
  </thead>

  <tbody>
    %s
  </tbody>
</table>
""" % (html_table_params, model, body)

def chains(session, model):
    if not hasattr(model, '_rmf_chains'):
        print("%s does not look like an RMF model" % model)
    else:
        session.logger.info(_chains_html(model), is_html=True)

chains_desc = CmdDesc(required=[("model", ModelArg)])
