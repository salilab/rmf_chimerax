# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.toolshed import BundleAPI


# Subclass from chimerax.core.toolshed.BundleAPI and
# override the method for opening files,
# inheriting all other methods from the base class.
class _MyAPI(BundleAPI):

    api_version = 1

    @staticmethod
    def register_command(bi, ci, logger):
        from . import cmd
        if ci.name == "rmf hierarchy":
            func = cmd.hierarchy
            desc = cmd.hierarchy_desc
        elif ci.name == "rmf chains":
            func = cmd.chains
            desc = cmd.chains_desc
        elif ci.name == "rmf readtraj":
            func = cmd.readtraj
            desc = cmd.readtraj_desc
        else:
            raise ValueError(
                "trying to register unknown command: %s" % ci.name)
        if desc.synopsis is None:
            desc.synopsis = ci.synopsis
        from chimerax.core.commands import register
        register(ci.name, desc, func)

    @staticmethod
    def start_tool(session, bi, ti):
        # bi is an instance of chimerax.core.toolshed.BundleInfo
        # ti is an instance of chimerax.core.toolshed.ToolInfo
        if ti.name == "RMF Viewer":
            from . import tool
            return tool.RMFViewer(session, ti.name)
        raise ValueError("trying to start unknown tool: %s" % ti.name)

    # Override method for opening file
    @staticmethod
    def run_provider(session, name, mgr, **kw):
        from . import io
        return io.RMFOpenerInfo()

    # Override method for opening file (old mechanism)
    @staticmethod
    def open_file(session, path, format_name):
        from .io import open_rmf
        return open_rmf(session, path)

    @staticmethod
    def get_class(class_name):
        io_classes = frozenset(
            ('_RMFModel', '_RMFState', '_RMFHierarchyNode',
             '_RMFFeature', '_RMFSampleProvenance',
             '_RMFDrawing', '_RMFScriptProvenance',
             '_RMFSoftwareProvenance', '_RMFStructureProvenance',
             '_RMFXLMSRestraintProvenance', '_RMFEMRestraintGMMProvenance',
             '_RMFEMRestraintMRCProvenance', '_RMFSAXSRestraintProvenance',
             '_RMFEM2DRestraintProvenance'))
        if class_name in io_classes:
            from . import io
            return getattr(io, class_name)
        elif class_name == 'RMFViewer':
            from . import tool
            return tool.RMFViewer
        raise ValueError("Unknown class name '%s'" % class_name)


# Create the ``bundle_api`` object that ChimeraX expects.
bundle_api = _MyAPI()
