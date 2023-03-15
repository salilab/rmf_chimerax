# vim: set expandtab shiftwidth=4 softtabstop=4:

import sys
import numpy
from chimerax.core.commands import CmdDesc
from chimerax.core.commands import IntArg, ModelArg


class _StateSelector:
    def __init__(self, istate):
        self.istate = istate
        self.seen_states = 0

    def is_selected(self):
        if self.seen_states == self.istate:
            return True
        self.seen_states += 1


def _print_hierarchy(node, depth, level=0):
    yield "<li>%s" % node.name
    if node.children and (depth < 0 or depth > level):
        yield "<ul>"
        for child in node.children:
            for h in _print_hierarchy(child, depth, level + 1):
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
        return ('<a title="Select chain" href="cxcmd:select #%s/%s">%s</a>'
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


class _RMFTrajectoryLoader:
    def __init__(self):
        pass

    def load(self, state, first, last, step):
        if sys.platform == 'darwin':
            from .mac import RMF
        elif sys.platform == 'linux':
            from .linux import RMF
        else:
            from .windows import RMF

        model = state.parent
        istate = model.child_models().index(state)
        r = RMF.open_rmf_file_read_only(model.rmf_filename)
        self.statef = RMF.StateConstFactory(r)
        self.particlef = RMF.ParticleConstFactory(r)
        self.ballf = RMF.BallConstFactory(r)

        numframes = r.get_number_of_frames()
        if last is None or last >= numframes:
            last = numframes - 1
        frames_to_read = range(first, last + 1, step)
        if len(frames_to_read) == 0:
            return 0

        state_node = self._get_state_node(r, istate)
        coords = numpy.empty((len(state.atoms), 3))
        for nframe in frames_to_read:
            r.set_current_frame(RMF.FrameID(nframe))
            RMF.get_all_global_coordinates(r, state_node, coords)
            state.add_coordset(nframe + 1, coords)
        return len(frames_to_read)

    def _get_state_node(self, r, istate):
        """Return the RMF node corresponding to the istate'th state"""
        def _check_node(node, root, statesel):
            if self.statef.get_is(node):
                if statesel.is_selected():
                    return node
            elif self.ballf.get_is(node) or self.particlef.get_is(node):
                # If we found coordinates, we must have no states, so
                # return the top level ("unnamed state")
                return root
            else:  # don't descend into unwanted states
                for child in node.get_children():
                    found = _check_node(child, root, statesel)
                    if found is not None:
                        return found
        statesel = _StateSelector(istate)
        root = r.get_root_node()
        c = _check_node(root, root, statesel)
        if c is None:
            raise ValueError("Couldn't find state #%d" % istate)
        return c


def readtraj(session, model, first=0, last=None, step=1):
    if (not hasattr(model, 'atoms') or model.parent is None
            or not hasattr(model.parent, 'rmf_filename')):
        print("%s does not look like an RMF state" % model)
        return
    t = _RMFTrajectoryLoader()
    numframes = t.load(model, first, last, step)
    if numframes:
        session.logger.info(
            "Read %d frames into coordset; use 'coordset slider #%s' to view"
            % (numframes, model.id_string))
    else:
        session.logger.warning("No frames were read")


readtraj_desc = CmdDesc(required=[("model", ModelArg)],
                        optional=[("first", IntArg),
                                  ("last", IntArg),
                                  ("step", IntArg)])
