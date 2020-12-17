# vim: set expandtab shiftwidth=4 softtabstop=4:

import numpy
import os.path
import sys
import weakref
import copy

from chimerax.atomic import Atom, Atoms, Bond, Pseudobond


class _MockRMFNode:
    __slots__ = ['name', 'rmf_index']

    def __init__(self, data):
        self.name, self.rmf_index = data['name'], data['rmf_index']

    def get_name(self):
        return self.name

    def get_index(self):
        return self.rmf_index


try:
    import chimerax.open_command

    class RMFOpenerInfo(chimerax.open_command.OpenerInfo):
        def open(self, session, data, file_name, **kw):
            return open_rmf(session, data)
except ImportError:
    pass


def open_rmf(session, path):
    """Read an RMF file from a named file.

    Returns the 2-tuple return value appropriate for the
    ``chimerax.core.toolshed.BundleAPI.open_file`` method.
    """
    rl = _RMFLoader()
    r, structures = rl.load(path, session)

    numframes = r.get_number_of_frames()
    producer = r.get_producer()
    status = ("Opened RMF file%s with %d frame%s."
              % (" produced with %s," % producer if producer else "",
                 numframes, "" if numframes == 1 else "s"))
    if structures[0]._rmf_resolutions:
        status += (" Representation read at the following resolutions: %s."
                   % ", ".join("%.1f" % i for i in
                               sorted(structures[0]._rmf_resolutions)))
    if numframes > 1:
        status += (" Only the first frame was read; to read additional "
                   "frames, use the 'rmf readtraj' command.")
    if session.ui.is_gui:
        from chimerax.core.commands import run
        run(session, 'tool show "RMF Viewer"', log=False)
    return structures, status


from chimerax.core.state import State
from chimerax.core.models import Model
from chimerax.atomic import Structure, AtomicStructure, AtomicShapeDrawing


class _RMFState(AtomicStructure):
    """Representation of structure corresponding to a single RMF state"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._features = None
        # Assume the structure is atomic until we encounter coordinates without
        # atomic information
        self._atomic = True

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'atomic structure state':
                    AtomicStructure.take_snapshot(self, session, flags)}
        return data

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFState(session, auto_style=False, log_info=False)
        s.set_state_from_snapshot(session, data)
        return s

    def set_state_from_snapshot(self, session, data):
        self._as_set_state_from_snapshot(
            session, data['atomic structure state'])

    def _as_set_state_from_snapshot(self, session, data):
        # AtomicStructure doesn't provide a set_state_from_snapshot method,
        # so duplicate its restore_snapshot functionality
        if data.get('AtomicStructure version', 1) == 1:
            Structure.set_state_from_snapshot(self, session, data)
        else:
            from chimerax.atomic.molobject import set_custom_attrs
            Structure.set_state_from_snapshot(
                self, session, data['structure state'])
            set_custom_attrs(self, data)

    def _add_pseudobond(self, atoms):
        f = self._get_features()
        b = f.new_pseudobond(*atoms)
        b.halfbond = False
        return b

    def _get_features(self):
        """Get the pseudobond group used to display RMF features"""
        if self._features is None:
            self._features = self.pseudobond_group("Features")
        return self._features

    def apply_auto_styling(self, *args, **kwargs):
        # Only apply auto styling for truly atomic structures
        if self._atomic:
            super().apply_auto_styling(*args, **kwargs)


class _RMFDrawing(Structure):
    """Representation of RMF geometry"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drawing = AtomicShapeDrawing('geometry')
        self.add_drawing(self._drawing)

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'drawing': self._drawing,
                'structure state':
                    Structure.take_snapshot(self, session, flags)}
        return data

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFDrawing(session)
        s.set_state_from_snapshot(session, data)
        return s

    def set_state_from_snapshot(self, session, data):
        Structure.set_state_from_snapshot(self, session,
                                          data['structure state'])
        self._drawing = data['drawing']
        self.add_drawing(self._drawing)


class _RMFModel(Model):
    """Representation of the top level of an RMF model"""
    def __init__(self, session, filename):
        name = os.path.splitext(os.path.basename(filename))[0]
        self._unnamed_state = None
        self._drawing = None
        self._provenance = None
        self._provenance_map = {}
        self._rmf_resolutions = set()
        # We always want to show nodes with no explicit resolution
        self._selected_rmf_resolutions = set((None,))
        self._rmf_chains = []
        super().__init__(name, session)

    def take_snapshot(self, session, flags):
        pm = {filename: model.id
              for filename, model in self._provenance_map.items()
              if not model.was_deleted}
        data = {'version': 1,
                'model state': Model.take_snapshot(self, session, flags),
                'rmf_filename': self.rmf_filename,
                'rmf_features': self.rmf_features,
                'rmf_provenance': self.rmf_provenance,
                'rmf_hierarchy': self.rmf_hierarchy,
                'provenance_map': pm,
                'rmf_resolutions': self._rmf_resolutions,
                'selected_rmf_resolutions': self._selected_rmf_resolutions,
                'rmf_chains': self._rmf_chains}
        return data

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFModel(session, '')
        s.set_state_from_snapshot(session, data)
        # Map session data back to ChimeraX objects only after all models have
        # been loaded (and not later, since they refer to model IDs and atom
        # indices which could be changed by the user after session-load)
        session.triggers.add_handler(
            'end restore session',
            lambda trigger, session, model=s:
            _restore_chimera_obj(session, model))
        return s

    def set_state_from_snapshot(self, session, data):
        Model.set_state_from_snapshot(self, session, data['model state'])
        self.rmf_filename = data['rmf_filename']
        self.rmf_features = data['rmf_features']
        self.rmf_provenance = data['rmf_provenance']
        self.rmf_hierarchy = data['rmf_hierarchy']
        self._provenance_map = data['provenance_map']
        self._rmf_resolutions = data['rmf_resolutions']
        self._selected_rmf_resolutions = data['selected_rmf_resolutions']
        self._rmf_chains = data['rmf_chains']

    def _add_rmf_resolution(self, res):
        self._rmf_resolutions.add(res)
        self._selected_rmf_resolutions.add(res)

    def get_drawing(self):
        if self._drawing is None:
            self._drawing = _RMFDrawing(self.session, name="Geometry")
            self.add([self._drawing])
        return self._drawing

    def _has_provenance(self, name):
        """Return True iff provenance from the given name has been read"""
        return name in self._provenance_map

    def _update_provenance_map(self):
        """Make sure that provenance mapping is up to date, by deleting
           references to models that have been closed since the map was
           last modified."""
        to_delete = [name for name, model
                     in self._provenance_map.items() if model.was_deleted]
        for name in to_delete:
            del self._provenance_map[name]

    def _add_provenance(self, name, p):
        """Add a Model containing provenance information keyed by the given
           name (usually a filename)"""
        if self._provenance is None or self._provenance.was_deleted:
            self._provenance = Model('Provenance', self.session)
            self.add([self._provenance])
        self._provenance_map[name] = p
        self._provenance.add([p])
        return self._provenance

    def _add_state(self, name):
        """Create and return a new _RMFState"""
        s = _RMFState(self.session, name=name)
        self.add([s])
        return s

    def _add_rmf_chain(self, chain, hierarchy):
        self._rmf_chains.append((chain.get_chain_id(), hierarchy))

    def get_unnamed_state(self):
        """Get the 'unnamed' state, used for structure that isn't the
           child of an RMF State node."""
        if self._unnamed_state is None:
            self._unnamed_state = self._add_state('Unnamed state')
        return self._unnamed_state

    def add_shape(self, vertices, normals, triangles, name):
        drawing = self.get_drawing()
        drawing._drawing.add_shape(vertices, normals, triangles,
                                   numpy.array([255, 255, 255, 255]),
                                   description=name)


class _RMFHierarchyNode(State):
    """Represent a single RMF node.
       Note that features (restraints) are stored outside of this hierarchy,
       as _RMFFeature objects, as are provenance nodes."""
    __slots__ = ['name', 'rmf_index', 'children', 'parent', 'chimera_obj',
                 'resolution', '_filtered_children']

    def __init__(self, rmf_node):
        self.name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.children = []
        self.resolution = None
        self._filtered_children = self.children
        self.chimera_obj = None
        self.parent = None

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'name': self.name,
                'rmf_index': self.rmf_index,
                'resolution': self.resolution,
                'chimera_obj': _save_snapshot_chimera_obj(self.chimera_obj),
                'children': self.children}
        return data

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFHierarchyNode(_MockRMFNode(data))
        s.resolution = data['resolution']
        s.chimera_obj = data['chimera_obj']
        s.add_children(data['children'])
        return s

    def add_children(self, children):
        for child in children:
            self.children.append(child)
            # avoid circular reference
            child.parent = weakref.ref(self)


def _save_snapshot_chimera_obj(obj):
    """Snapshot a Chimera object. We can't store these directly in the session
       (and rely on ChimeraX's own snapshot code) since this would result
       in a circular reference (since they refer to the model, which also
       holds the top-level rmf_hierarchy or rmf_features list)"""
    if obj is None:
        return None
    if isinstance(obj, Atoms):
        data = {'type': 'Atoms',
                'indices': obj.coord_indices}
        if obj.single_structure:
            data['single_structure'] = obj.structures[0].id
        else:
            data['structures'] = [s.id for s in obj.structures]
        return data
    elif isinstance(obj, Atom):
        data = {'type': 'Atom',
                'index': obj.coord_index,
                'structure': obj.structure.id}
        return data
    elif isinstance(obj, Bond):
        s = obj.atoms[0].structure
        data = {'type': 'Bond',
                'index': s.bonds.index(obj),
                'structure': s.id}
        return data
    elif isinstance(obj, Pseudobond):
        s = obj.atoms[0].structure
        data = {'type': 'Pseudobond',
                'structure': s.id,
                'index': s._features.pseudobonds.index(obj)}
        return data
    raise TypeError("Don't know how to snapshot %s" % str(obj))


def _load_snapshot_chimera_obj(session, data, model_by_id):
    """Map data from _save_snapshot_chimera_obj back to a ChimeraX object"""
    if data is None:
        return None
    elif data['type'] == 'Atoms':
        if 'single_structure' in data:
            m = model_by_id[data['single_structure']]
            atoms = [m.atoms[x] for x in data['indices']]
        else:
            atoms = []
            for s, ind in zip(data['structures'], data['indices']):
                atoms.append(model_by_id[s].atoms[ind])
        obj = Atoms(atoms)
        return obj
    elif data['type'] == 'Atom':
        return model_by_id[data['structure']].atoms[data['index']]
    elif data['type'] == 'Bond':
        return model_by_id[data['structure']].bonds[data['index']]
    elif data['type'] == 'Pseudobond':
        f = model_by_id[data['structure']]._get_features()
        obj = f.pseudobonds[data['index']]
        return obj
    raise TypeError("Don't know how to load snapshot %s" % str(data))


def _restore_nodes_chimera_obj(session, nodes, model_by_id):
    """Replace chimera_obj session data with actual objects for all listed
       nodes"""
    for n in nodes:
        n.chimera_obj = _load_snapshot_chimera_obj(session, n.chimera_obj,
                                                   model_by_id)
        _restore_nodes_chimera_obj(session, n.children, model_by_id)


def _restore_chimera_obj(session, model):
    """Replace chimera_obj session data with actual objects for the given
       RMF model"""
    model_by_id = {m.id: m for m in session.models.list()}

    model._provenance_map = {
        filename: model_by_id[mid]
        for filename, mid in model._provenance_map.items()}
    _restore_nodes_chimera_obj(session, model.rmf_features, model_by_id)
    _restore_nodes_chimera_obj(session, [model.rmf_hierarchy], model_by_id)

    # Only need to call this once per model
    from chimerax.core.triggerset import DEREGISTER
    return DEREGISTER


class _RMFFeature(State):
    """Represent a single feature in an RMF file."""

    __slots__ = ['name', 'rmf_index', 'chimera_obj', 'children', 'parent']

    def __init__(self, rmf_node):
        self.name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.children = []
        self.chimera_obj = None
        self.parent = None

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'name': self.name,
                'rmf_index': self.rmf_index,
                'chimera_obj': _save_snapshot_chimera_obj(self.chimera_obj),
                'children': self.children}
        return data

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFFeature(_MockRMFNode(data))
        for child in data['children']:
            s.add_child(child)
        s.chimera_obj = data['chimera_obj']
        return s

    def add_child(self, child):
        self.children.append(child)
        # avoid circular reference
        child.parent = weakref.ref(self)


class _RMFProvenance(State):
    """Represent some provenance of the RMF file."""

    _snapshot_keys = []

    def __init__(self, rmf_node):
        self._name = rmf_node.get_name()
        self.rmf_index = rmf_node.get_index()
        self.chimera_obj = None
        self.previous = None
        self.next = None
        self.hierarchy_node = None

    def set_previous(self, previous):
        """Add another _RMFProvenance node that represents the previous state
           of the system"""
        self.previous = previous
        previous.next = weakref.proxy(self)

    def load(self, session, model):
        """Override to load file(s) referenced by this object into the
           given session and model."""
        pass

    def take_snapshot(self, session, flags):
        data = {'version': 1,
                'name': self._name,
                'rmf_index': self.rmf_index,
                'previous': self.previous,
                'hierarchy_node': self.hierarchy_node}
        for k in self._snapshot_keys:
            data[k] = getattr(self, k)
        return data

    def set_state_from_snapshot(self, data):
        self.hierarchy_node = data['hierarchy_node']
        if data['previous']:
            self.set_previous(data['previous'])

    # Displayed name of this provenance (defaults to the name of the RMF node)
    name = property(lambda self: self._name)


def _atomic_model_reader(filename):
    """Get a ChimeraX function to read the given atomic model (PDB, mmCIF)"""
    if filename.endswith('.cif'):
        from chimerax.mmcif import open_mmcif
        return open_mmcif
    elif filename.endswith('.pdb'):
        from chimerax.pdb import open_pdb
        return open_pdb


def _prune_chains(model, chains):
    """Delete all but the given chains from the model"""
    atoms_to_del = [atoms for _, cid, atoms in model.atoms.by_chain
                    if cid not in chains]
    for atoms in atoms_to_del:
        atoms.delete()


class _RMFStructureProvenance(_RMFProvenance):
    """Represent a structure file (PDB, mmCIF) used as input for an RMF"""

    _snapshot_keys = ['chain', 'residue_offset', 'filename', 'allchains']

    def __init__(self, rmf_node, prov, provenance_chains):
        super().__init__(rmf_node)
        #: The chain ID used in the given file
        self.chain = prov.get_chain()
        #: Value to add to RMF residue numbers to get residue numbers
        #: in the file (usually zero)
        self.residue_offset = prov.get_residue_offset()
        #: Full path to PDB/mmCIF file
        self.filename = prov.get_filename()
        # Keep track of *all* chains we're interested in in this structure
        # (across all provenance nodes in the RMF file)
        self.allchains = provenance_chains.setdefault(self.filename, set())
        self.allchains.add(self.chain)

    @staticmethod
    def restore_snapshot(session, data):
        class MockStructureProvenance:
            def __init__(self, data):
                self.data = data

            def get_chain(self):
                return self.data['chain']

            def get_residue_offset(self):
                return self.data['residue_offset']

            def get_filename(self):
                return self.data['filename']
        s = _RMFStructureProvenance(_MockRMFNode(data),
                                    MockStructureProvenance(data), {})
        s.set_state_from_snapshot(data)
        return s

    def set_state_from_snapshot(self, data):
        _RMFProvenance.set_state_from_snapshot(self, data)
        self.allchains = data['allchains']

    def load(self, session, model):
        # Note that we load all chains referenced by the RMF file, as this is
        # more efficient than creating a separate model for each chain.
        if model._has_provenance(self.filename):
            return
        if not os.path.exists(self.filename):
            session.logger.warning("Not reading %s; does not exist"
                                   % self.filename)
        else:
            open_model = _atomic_model_reader(self.filename)
            if open_model:
                with open(self.filename) as fh:
                    models, msg = open_model(
                        session, fh, os.path.basename(self.filename),
                        auto_style=False, log_info=False)
                    _prune_chains(models[0], self.allchains)
                model._add_provenance(self.filename, models[0])
            else:
                session.logger.warning("Not reading %s; file format "
                                       "not recognized" % self.filename)

    def _get_name(self):
        return ("Chain %s from %s"
                % (self.chain, os.path.basename(self.filename)))
    name = property(_get_name)


class _RMFSampleProvenance(_RMFProvenance):
    """Information about how an RMF model was sampled"""

    _snapshot_keys = ['frames', 'iterations', 'method', 'replicas']

    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: Number of frames generated in the sampling
        self.frames = prov.get_frames()
        #: Number of scoring function iterations per frame
        self.iterations = prov.get_iterations()
        #: Sampling method used (e.g. Monte Carlo)
        self.method = prov.get_method()
        #: Number of replicas used in replica exchange sampling
        self.replicas = prov.get_replicas()

    @staticmethod
    def restore_snapshot(session, data):
        class MockSampleProvenance:
            def __init__(self, data):
                self.data = data

            def get_frames(self):
                return self.data['frames']

            def get_iterations(self):
                return self.data['iterations']

            def get_method(self):
                return self.data['method']

            def get_replicas(self):
                return self.data['replicas']
        s = _RMFSampleProvenance(
            _MockRMFNode(data), MockSampleProvenance(data))
        s.set_state_from_snapshot(data)
        return s

    def _get_name(self):
        return ("Sampling using %s making %d frames"
                % (self.method, self.frames))
    name = property(_get_name)


class _RMFScriptProvenance(_RMFProvenance):
    """Information about the script used to build an RMF model"""

    _snapshot_keys = ['filename']

    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: Full path to the script
        self.filename = prov.get_filename()

    @staticmethod
    def restore_snapshot(session, data):
        class MockScriptProvenance:
            def __init__(self, data):
                self.data = data

            def get_filename(self):
                return self.data['filename']
        s = _RMFScriptProvenance(
            _MockRMFNode(data), MockScriptProvenance(data))
        s.set_state_from_snapshot(data)
        return s

    def _get_name(self):
        return ("Using script %s" % self.filename)
    name = property(_get_name)


class _RMFSoftwareProvenance(_RMFProvenance):
    """Information about the software used to build an RMF model"""

    _snapshot_keys = ['location', 'software_name', 'version']

    def __init__(self, rmf_node, prov):
        super().__init__(rmf_node)
        #: URL to obtain the software
        self.location = prov.get_location()
        #: Name of the software package
        self.software_name = prov.get_name()
        #: Version of the software used
        self.version = prov.get_version()

    @staticmethod
    def restore_snapshot(session, data):
        class MockSoftwareProvenance:
            def __init__(self, data):
                self.data = data

            def get_location(self):
                return self.data['location']

            def get_name(self):
                return self.data['software_name']

            def get_version(self):
                return self.data['version']
        s = _RMFSoftwareProvenance(_MockRMFNode(data),
                                   MockSoftwareProvenance(data))
        s.set_state_from_snapshot(data)
        return s

    def _get_name(self):
        return ("Using software %s version %s from %s" %
                (self.software_name, self.version, self.location))
    name = property(_get_name)


class _RMFEMRestraintGMMProvenance(_RMFProvenance):
    """Information about an electron microscopy restraint read from GMMs"""

    _snapshot_keys = ['filename']

    def __init__(self, rmf_node, filename):
        super().__init__(rmf_node)
        self.filename = filename
        # The original MRC file (if known)
        mrc = self._parse_gmm(rmf_node, filename)
        if mrc:
            self.set_previous(mrc)

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFEMRestraintGMMProvenance(_MockRMFNode(data), data['filename'])
        s.set_state_from_snapshot(data)
        return s

    def _parse_gmm(self, rmf_node, filename):
        """Extract metadata from the GMM file (to find the original MRC file)
           if available"""
        if not os.path.exists(filename):
            return
        with open(filename) as fh:
            for line in fh:
                if line.startswith('# data_fn: '):
                    relpath = line[11:].rstrip('\r\n')
                    fname = os.path.join(os.path.dirname(filename), relpath)
                    return _RMFEMRestraintMRCProvenance(rmf_node, fname)

    def load(self, session, model):
        if self.previous:
            self.previous.load(session, model)

    def _get_name(self):
        return ("Gaussian Mixture Model from %s"
                % os.path.basename(self.filename))
    name = property(_get_name)


class _RMFEMRestraintMRCProvenance(_RMFProvenance):
    """Information about an electron microscopy restraint read from MRC"""

    _snapshot_keys = ['filename']

    def __init__(self, rmf_node, filename):
        super().__init__(rmf_node)
        self.filename = filename

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFEMRestraintMRCProvenance(_MockRMFNode(data), data['filename'])
        s.set_state_from_snapshot(data)
        return s

    def load(self, session, model):
        if not model._has_provenance(self.filename):
            from chimerax.map.volume import open_map
            from chimerax.map_data import UnknownFileType
            try:
                maps, msg = open_map(session, self.filename)
            except UnknownFileType:
                return
            v = maps[0]
            v.set_display_style('image')
            v.show()
            model._add_provenance(self.filename, v)

    def _get_name(self):
        return "EM map from %s" % os.path.basename(self.filename)
    name = property(_get_name)


class _RMFXLMSRestraintProvenance(_RMFProvenance):
    """Information about an XL-MS restraint"""

    _snapshot_keys = ['filename']

    def __init__(self, rmf_node, filename):
        super().__init__(rmf_node)
        self.filename = filename

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFXLMSRestraintProvenance(_MockRMFNode(data), data['filename'])
        s.set_state_from_snapshot(data)
        return s

    def _get_name(self):
        return "XL-MS data from %s" % os.path.basename(self.filename)
    name = property(_get_name)


class _RMFSAXSRestraintProvenance(_RMFProvenance):
    """Information about a SAXS restraint"""

    _snapshot_keys = ['filename']

    def __init__(self, rmf_node, filename):
        super().__init__(rmf_node)
        self.filename = filename

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFSAXSRestraintProvenance(_MockRMFNode(data), data['filename'])
        s.set_state_from_snapshot(data)
        return s

    def _get_name(self):
        return "SAXS profile from %s" % os.path.basename(self.filename)
    name = property(_get_name)


class _RMFEM2DRestraintProvenance(_RMFProvenance):
    """Information about a 2D EM restraint"""

    _snapshot_keys = ['filename', 'pixel_size']

    def __init__(self, rmf_node, filename, pixel_size):
        super().__init__(rmf_node)
        self.filename = filename
        self.pixel_size = pixel_size

    @staticmethod
    def restore_snapshot(session, data):
        s = _RMFEM2DRestraintProvenance(
            _MockRMFNode(data), data['filename'], data['pixel_size'])
        s.set_state_from_snapshot(data)
        return s

    def load(self, session, model):
        if not model._has_provenance(self.filename):
            from chimerax.map.volume import open_map
            from chimerax.map_data import UnknownFileType
            try:
                maps, msg = open_map(session, self.filename)
            except UnknownFileType:
                return
            v = maps[0]
            v.data.set_step((self.pixel_size, self.pixel_size, v.data.step[2]))
            # todo: set orientation
            v.set_display_style('image')
            v.show()
            model._add_provenance(self.filename, v)

    def _get_name(self):
        return "EM class average from %s" % os.path.basename(self.filename)
    name = property(_get_name)


class _RMFHierarchyInfo(object):
    """Track structural information encountered through the RMF hierarchy"""
    def __init__(self, top_level):
        self.top_level = top_level
        self._refframe = self._state = self._chain = self._copy = None
        self._resolution = self._resnum = self._restype = None
        self._residue = None
        self._resnum_for_chain = {}

    def _set_reference_frame(self, rf):
        """Set the current reference frame from an RMF ReferenceFrame node"""
        from scipy.spatial.transform import Rotation
        rot = rf.get_rotation()
        # RMF quaternions are scalar-first; scipy uses scalar-last
        rot = Rotation.from_quat((rot[1], rot[2], rot[3], rot[0]))
        tran = numpy.array(rf.get_translation())
        if self._refframe:
            # Compose with existing transformation
            oldrot, oldtran = self._refframe
            tran = oldrot.apply(tran) + oldtran
            rot = oldrot * rot
        self._refframe = (rot, tran)

    def handle_node(self, node, hierarchy, loader):
        """Extract structural information from the given RMF node.
           Return the _RMFHierarchyInfo object containing this information.
           This may be the current object, or a new one."""
        def copy_if_needed(x):
            # Make a copy if we need to so we don't mess with the information
            # used by parent nodes
            if x is self:
                return copy.copy(x)
            else:
                return x
        rhi = self
        if loader.statef.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._state = self.top_level._add_state(node.get_name())
        if loader.refframef.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._set_reference_frame(loader.refframef.get(node))
        if loader.chainf.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._chain = (node, loader.chainf.get(node))
            self.top_level._add_rmf_chain(rhi._chain[1], hierarchy)
        if loader.copyf.get_is(node):
            rhi = copy_if_needed(rhi)
            rhi._copy = loader.copyf.get(node).get_copy_index()
        if loader.resolutionf.get_is(node):
            rhi = copy_if_needed(rhi)
            n = loader.resolutionf.get(node)
            rhi._resolution = n.get_explicit_resolution()
            self.top_level._add_rmf_resolution(rhi._resolution)
        if loader.fragmentf.get_is(node):
            rhi = copy_if_needed(rhi)
            f = loader.fragmentf.get(node)
            resinds = f.get_residue_indexes()
            rhi._residue = None  # clear residue cache
            rhi._resnum = resinds[len(resinds) // 2]
            rhi._restype = 'UNK'  # Guess type
        if loader.residuef.get_is(node):
            rhi = copy_if_needed(rhi)
            r = loader.residuef.get(node)
            rhi._residue = None  # clear residue cache
            rhi._resnum = r.get_residue_index()
            rhi._restype = r.get_residue_type()
        return rhi

    def get_state(self):
        """Get the current state"""
        if self._state:
            return self._state
        else:
            # If we're not under a State node, use the unnamed state
            return self.top_level.get_unnamed_state()

    def get_residue(self):
        """Get the current residue"""
        if self._residue is None:  # Use cached residue if available
            state = self.get_state()
            if self._chain is None:
                chain_id = 'X'
            else:
                chain_id = self._chain[1].get_chain_id()
            if self._resnum is None:
                # If RMF provides no residue info, make it up
                resnum = self._resnum_for_chain.setdefault(chain_id, 0) + 1
                self._residue = state.new_residue('UNK', chain_id, resnum)
                self._resnum_for_chain[chain_id] = resnum
            else:
                self._residue = state.new_residue(self._restype, chain_id,
                                                  self._resnum)
            if self._chain:
                self._residue.rmf_name = self._chain[0].get_name()
            if self._copy is not None:
                self._residue.copy = self._copy
            if self._resolution is not None:
                self._residue.resolution = self._resolution
        return self._residue

    def new_atom(self, p, mass, name=None, element='C'):
        """Create and return a new ChimeraX Atom for the given Particle
           (and Atom, if applicable) node.
           Call add_atom() to complete adding the atom to the model."""
        state = self.get_state()
        if name is None:
            name = 'C'
            state._atomic = False
        atom = state.new_atom(name, element)
        atom.coord = p.get_coordinates()
        if self._refframe:
            rot, trans = self._refframe
            atom.coord = rot.apply(atom.coord) + trans
        atom.mass = mass
        atom.radius = p.get_radius()
        atom.draw_mode = atom.SPHERE_STYLE
        return atom

    def new_bond(self, a1, a2):
        state = a1.structure
        return state.new_bond(a1, a2)

    def new_feature(self, atoms):
        if len(atoms) == 2:
            # Make and return a pseudobond if the feature acts on 2 atoms
            state = atoms[0].structure
            return state._add_pseudobond(atoms)
        else:
            # Otherwise, return the list of atoms the feature acts on
            return Atoms(atoms)

    def new_segment(self, coords, name):
        # todo: don't rely on chimerax.bild (not public API)
        from chimerax.bild.bild import get_cylinder
        if len(coords) != 2:
            return
        a = numpy.array(coords[0])
        b = numpy.array(coords[1])
        # Skip zero-length lines
        if numpy.linalg.norm(a - b) < 1e-6:
            return
        vertices, normals, triangles = get_cylinder(1.0, a, b)
        self.top_level.add_shape(vertices, normals, triangles, name)

    def add_atom(self, atom):
        residue = self.get_residue()
        residue.add_atom(atom)


class _RMFLoader(object):
    """Load information from an RMF file"""

    _feature_provenance_class = {
        'IMP.isd.GaussianEMRestraint': _RMFEMRestraintGMMProvenance,
        'IMP.pmi.CrossLinkingMassSpectrometryRestraint':
            _RMFXLMSRestraintProvenance,
        'IMP.saxs.Restraint': _RMFSAXSRestraintProvenance,
    }

    def __init__(self):
        pass

    def load(self, path, session):
        if sys.platform == 'darwin':
            from .mac import RMF
        elif sys.platform == 'linux':
            from .linux import RMF
        else:
            from .windows import RMF

        self.GAUSSIAN_PARTICLE = RMF.GAUSSIAN_PARTICLE
        self.PARTICLE = RMF.PARTICLE
        self.PROVENANCE = RMF.PROVENANCE

        r = RMF.open_rmf_file_read_only(path)
        self.particlef = RMF.ParticleConstFactory(r)
        self.gparticlef = RMF.GaussianParticleConstFactory(r)
        self.ballf = RMF.BallConstFactory(r)
        self.strucprovf = RMF.StructureProvenanceConstFactory(r)
        self.sampleprovf = RMF.SampleProvenanceConstFactory(r)
        self.scriptprovf = RMF.ScriptProvenanceConstFactory(r)
        self.softwareprovf = RMF.SoftwareProvenanceConstFactory(r)
        self.coloredf = RMF.ColoredConstFactory(r)
        self.chainf = RMF.ChainConstFactory(r)
        self.fragmentf = RMF.FragmentConstFactory(r)
        self.residuef = RMF.ResidueConstFactory(r)
        self.refframef = RMF.ReferenceFrameConstFactory(r)
        self.statef = RMF.StateConstFactory(r)
        self.bondf = RMF.BondConstFactory(r)
        self.represf = RMF.RepresentationConstFactory(r)
        self.altf = RMF.AlternativesConstFactory(r)
        self.copyf = RMF.CopyConstFactory(r)
        self.resolutionf = RMF.ExplicitResolutionConstFactory(r)
        self.atomf = RMF.AtomConstFactory(r)
        self.segmentf = RMF.SegmentConstFactory(r)
        self.rmf_index_to_atom = {}

        imp_restraint_cat = r.get_category("IMP restraint")
        keys = dict((r.get_name(k), k)
                    for k in r.get_keys(imp_restraint_cat))
        self.rsr_typek = keys.get('type')
        self.rsr_pixelsizek = keys.get('pixel size')

        imp_restraint_fn_cat = r.get_category("IMP restraint files")
        keys = dict((r.get_name(k), k)
                    for k in r.get_keys(imp_restraint_fn_cat))
        self.rsr_filenamek = keys.get('filename')
        self.rsr_imagefilesk = keys.get('image files')

        r.set_current_frame(RMF.FrameID(0))

        top_level = _RMFModel(session, path)
        rhi = _RMFHierarchyInfo(top_level)
        top_level.rmf_filename = os.path.abspath(path)
        top_level.rmf_features = []
        top_level.rmf_provenance = []
        # The set of chain IDs to read from each named input structure file
        _provenance_chains = {}
        top_level.rmf_hierarchy, = self._handle_node(r.get_root_node(), rhi,
                                                     top_level.rmf_features,
                                                     top_level.rmf_provenance,
                                                     os.path.dirname(path),
                                                     _provenance_chains, None)
        return r, [top_level]

    def _add_atom(self, node, p, mass, rhi):
        if self.atomf.get_is(node):
            ap = self.atomf.get(node)
            name = node.get_name()
            # ChimeraX names must not exceed 4 characters, so strip RMF/IMP
            # HET: prefix if present
            if name.startswith('HET:'):
                name = name[4:].strip()
            atom = rhi.new_atom(p, mass, name=name, element=ap.get_element())
        else:
            atom = rhi.new_atom(p, mass)
        self.rmf_index_to_atom[node.get_index()] = atom
        if self.coloredf.get_is(node):
            c = self.coloredf.get(node)
            # RMF colors are 0-1 and has no alpha; ChimeraX uses 0-255
            atom.color = [x * 255. for x in c.get_rgb_color()] + [255]
        rhi.add_atom(atom)
        return atom

    def _handle_provenance(self, node, provenance_chains, parent_node):
        if self.strucprovf.get_is(node):
            prov = _RMFStructureProvenance(node, self.strucprovf.get(node),
                                           provenance_chains)
        elif self.sampleprovf.get_is(node):
            prov = _RMFSampleProvenance(node, self.sampleprovf.get(node))
        elif self.scriptprovf.get_is(node):
            prov = _RMFScriptProvenance(node, self.scriptprovf.get(node))
        elif self.softwareprovf.get_is(node):
            prov = _RMFSoftwareProvenance(node, self.softwareprovf.get(node))
        else:
            prov = _RMFProvenance(node)
        # Provenance nodes *should* only have at most one "child"
        for child in node.get_children():
            prov.set_previous(self._handle_provenance(child, provenance_chains,
                                                      parent_node))
        prov.hierarchy_node = parent_node
        return prov

    def _handle_feature_provenance(self, node, rmf_dir):
        def get_node_filename(node):
            fname = node.get_value(self.rsr_filenamek)
            if fname:
                # path is relative to that of the RMF file
                return os.path.join(rmf_dir, fname)
        # noop if these keys aren't in the file at all
        if self.rsr_typek is None:
            return
        rsrtype = node.get_value(self.rsr_typek)
        if self.rsr_filenamek:
            cls = self._feature_provenance_class.get(rsrtype)
            if cls:
                fname = get_node_filename(node)
                if fname:
                    return cls(node, fname)
        if rsrtype == 'IMP.em2d.PCAFitRestraint':
            return self._make_em2d_provenance(node, rmf_dir)

    def _make_em2d_provenance(self, node, rmf_dir):
        if not self.rsr_imagefilesk or not self.rsr_pixelsizek:
            return
        pixel_size = node.get_value(self.rsr_pixelsizek)
        images = node.get_value(self.rsr_imagefilesk)
        if images and pixel_size:
            return [_RMFEM2DRestraintProvenance(
                node, os.path.join(rmf_dir, fname), pixel_size)
                for fname in images]

    def _handle_feature(self, node, parent_rhi, rmf_dir, provenance):
        feature = _RMFFeature(node)
        feature.chimera_obj = self._add_feature(
            self.represf.get(node), parent_rhi)
        # Extract provenance from restraint if present
        p = self._handle_feature_provenance(node, rmf_dir)
        if p:
            if isinstance(p, list):
                provenance.extend(p)
            else:
                provenance.append(p)
        for child in node.get_children():
            if self.represf.get_is(child):
                feature.add_child(self._handle_feature(child, parent_rhi,
                                                       rmf_dir, provenance))
        return feature

    def _handle_node(self, node, parent_rhi, features, provenance, rmf_dir,
                     provenance_chains, parent_node):
        # Features are handled outside of the regular hierarchy
        if self.represf.get_is(node):
            features.append(self._handle_feature(node, parent_rhi, rmf_dir,
                                                 provenance))
            return []

        # Provenance is handled outside of the regular hierarchy
        if node.get_type() == self.PROVENANCE:
            provenance.append(self._handle_provenance(node, provenance_chains,
                                                      parent_node))
            return []

        rmf_nodes = [_RMFHierarchyNode(node)]
        # Get hierarchy-related info from this node (e.g. chain, state)
        rhi = parent_rhi.handle_node(node, rmf_nodes[0], self)
        rmf_nodes[0].resolution = rhi._resolution
        if self.particlef.get_is(node):
            # todo: special handling for Gaussians; right now we assume that
            # every Gaussian is also a Particle, as 1) this is the case for
            # IMP-generated structures and 2) particlef.get_is() returns True
            # for Gaussians anyway (since it appears to only check for mass)
            p = self.particlef.get(node)
            atom = self._add_atom(node, p, p.get_mass(), rhi)
            rmf_nodes[0].chimera_obj = atom
        elif self.ballf.get_is(node):
            # balls have no mass
            atom = self._add_atom(node, self.ballf.get(node), 0., rhi)
            rmf_nodes[0].chimera_obj = atom
        if self.bondf.get_is(node):
            bond = self._add_bond(self.bondf.get(node), rhi)
            rmf_nodes[0].chimera_obj = bond
        if self.segmentf.get_is(node):
            self._add_segment(self.segmentf.get(node), node.get_name(), rhi)
        for child in node.get_children():
            rmf_nodes[0].add_children(self._handle_node(
                child, rhi, features, provenance, rmf_dir, provenance_chains,
                rmf_nodes[0]))
        # Handle any alternatives (usually different resolutions)
        # Alternatives replace the current node - they are not children of
        # it - so use parent_rhi, not rhi.
        if self.altf.get_is(node):
            alt = self.altf.get(node)
            # The node itself should be the first alternative, so ignore that
            for p in alt.get_alternatives(self.PARTICLE)[1:]:
                rmf_nodes.extend(self._handle_node(
                    p, parent_rhi, features,
                    provenance, rmf_dir, provenance_chains, rmf_nodes[0]))
            for gauss in alt.get_alternatives(self.GAUSSIAN_PARTICLE):
                rmf_nodes.extend(self._handle_node(
                    gauss, parent_rhi, features,
                    provenance, rmf_dir, provenance_chains, rmf_nodes[0]))
        return rmf_nodes

    def _add_bond(self, bond, rhi):
        rmfatom0 = bond.get_bonded_0()
        rmfatom1 = bond.get_bonded_1()
        atom0 = self.rmf_index_to_atom[rmfatom0.get_index()]
        atom1 = self.rmf_index_to_atom[rmfatom1.get_index()]
        return rhi.new_bond(atom0, atom1)

    def _add_feature(self, feature, rhi):
        atoms = [self.rmf_index_to_atom.get(x.get_index())
                 for x in feature.get_representation()]
        return rhi.new_feature([a for a in atoms if a is not None])

    def _add_segment(self, segment, name, rhi):
        rhi.new_segment(segment.get_coordinates_list(), name)
