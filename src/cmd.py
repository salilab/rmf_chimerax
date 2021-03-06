# vim: set expandtab shiftwidth=4 softtabstop=4:

import sys
import numpy
from scipy.spatial.transform import Rotation
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


class _RMFNode:
    __slots__ = ['refframe', 'coords', 'children']

    def __init__(self, refframe, coords):
        self.refframe, self.coords = refframe, coords
        self.children = []

    def add_child(self, child):
        self.children.append(child)


class _Coords:
    def __init__(self, coords):
        self.coords = coords
        self.natom = 0

    def add(self, xyz, refframe):
        if refframe:
            rot, trans = refframe
            xyz = rot.apply(xyz) + trans
        self.coords[self.natom] = xyz
        self.natom += 1


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
        self.GAUSSIAN_PARTICLE = RMF.GAUSSIAN_PARTICLE
        self.PARTICLE = RMF.PARTICLE

        model = state.parent
        istate = model.child_models().index(state)
        r = RMF.open_rmf_file_read_only(model.rmf_filename)
        self.statef = RMF.StateConstFactory(r)
        self.refframef = RMF.ReferenceFrameConstFactory(r)
        self.gparticlef = RMF.GaussianParticleConstFactory(r)
        self.particlef = RMF.ParticleConstFactory(r)
        self.ballf = RMF.BallConstFactory(r)
        self.altf = RMF.AlternativesConstFactory(r)

        numframes = r.get_number_of_frames()
        if last is None or last >= numframes:
            last = numframes - 1
        frames_to_read = range(first, last + 1, step)
        if len(frames_to_read) == 0:
            return 0

        r.set_current_frame(RMF.FrameID(frames_to_read[0]))
        top_node = _RMFNode(None, None)
        numatoms = self.get_rmf_nodes(self._get_state_node(r, istate),
                                      top_node)
        if numatoms != len(state.atoms):
            raise ValueError("atom number mismatch, %d vs %s"
                             % (numatoms, len(state.atoms)))
        coords = numpy.empty((numatoms, 3))
        self.add_rmf_coordinates(top_node, None, _Coords(coords))
        state.add_coordset(frames_to_read[0] + 1, coords)
        for nframe in frames_to_read[1:]:
            r.set_current_frame(RMF.FrameID(nframe))
            self.add_rmf_coordinates(top_node, None, _Coords(coords))
            state.add_coordset(nframe + 1, coords)
        return len(frames_to_read)

    def _get_ref_frame(self, rf, parent):
        rot = rf.get_rotation()
        # RMF quaternions are scalar-first; scipy uses scalar-last
        rot = Rotation.from_quat((rot[1], rot[2], rot[3], rot[0]))
        tran = numpy.array(rf.get_translation())
        if parent:
            # Compose with existing transformation
            oldrot, oldtran = parent
            tran = oldrot.apply(tran) + oldtran
            rot = oldrot * rot
        return rot, tran

    def add_rmf_coordinates(self, parent, parent_refframe, coords):
        for node in parent.children:
            if node.refframe is not None:
                refframe = self._get_ref_frame(node.refframe, parent_refframe)
            else:
                refframe = parent_refframe
            if node.coords is not None:
                coords.add(node.coords.get_coordinates(), refframe)
            self.add_rmf_coordinates(node, refframe, coords)

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

    def get_rmf_nodes(self, node, parent):
        """Traverse the RMF hierarchy, and collect handles for all nodes
           pertaining to coordinate for the given states"""
        numatoms = 0
        refframe = coords = thisnode = None
        if self.refframef.get_is(node):
            refframe = self.refframef.get(node)
        if self.ballf.get_is(node):
            numatoms += 1
            coords = self.ballf.get(node)
        elif self.particlef.get_is(node):
            numatoms += 1
            coords = self.particlef.get(node)
        if refframe is not None or coords is not None:
            thisnode = _RMFNode(refframe, coords)
            parent.add_child(thisnode)

        for child in node.get_children():
            numatoms += self.get_rmf_nodes(child, thisnode or parent)
        if self.altf.get_is(node):
            alt = self.altf.get(node)
            for p in alt.get_alternatives(self.PARTICLE)[1:]:
                numatoms += self.get_rmf_nodes(p, parent)
            for gauss in alt.get_alternatives(self.GAUSSIAN_PARTICLE):
                numatoms += self.get_rmf_nodes(gauss, parent)
        return numatoms


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
