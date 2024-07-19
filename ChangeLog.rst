0.16 - 2024-07-19
=================
 - Fix session save/load of RMFs containing clustering or filtering
   provenance nodes.

0.15 - 2023-12-21
=================
 - Update to work with ChimeraX 1.7.

0.14 - 2023-04-26
=================
 - Handle reading RMF files that contain particles without coordinates.

0.13 - 2023-03-15
=================
 - Trajectory reading (`rmf readtraj` command) is now much faster.

0.12 - 2023-03-08
=================
 - Update bundled copy of RMF to latest version, 1.4.1.
 - Support Apple Silicon (arm64/M1) by adding a universal Mac bundle.

0.11 - 2021-12-09
=================
 - Update to work with ChimeraX 1.3.

0.10 - 2021-05-18
=================
 - Update to work with ChimeraX 1.2.

0.9 - 2020-06-18
================
 - Fix loading of RMF files with ChimeraX 1.0 final.

0.8 - 2020-05-15
================
 - Fix installation with ChimeraX 1.0 RC.

0.7 - 2020-04-23
================
 - Show any SAXS profiles or EM class averages referenced by the RMF file.

0.6 - 2020-03-19
================
 - Allow filtering the hierarchy by resolution in the RMF Viewer tool.

0.5 - 2020-03-09
================
 - Handle nested RMF features.
 - Add support for ChimeraX sessions.

0.4 - 2020-03-05
================
 - Add basic support for Gaussian particles (they are shown as spheres).
 - Add support for provenance (information about how the model was generated)
   to the RMF Viewer tool. This can be used to read in external files to
   supplement the model, such as electron microscopy density maps or input
   PDB files.

0.3 - 2020-03-02
================
 - Add support for multiple RMF models to the RMF Viewer tool.
 - Add a Features view to the RMF Viewer tool which allows RMF
   features (usually restraints) to be selected in the structure
   by clicking on them in the list.
 - Enable ribbon representation for atomic RMF files.
 - Add an `rmf readtraj` command to read multiple frames from RMF files.

0.2 - 2020-02-25
================
 - Improved support for RMF files containing atomic information.
 - Add basic visualization of RMF geometry, such as bounding boxes.
 - Add an `rmf hierarchy` command to show the RMF hierarchy in the log.
 - Add an `rmf chains` command to show the RMF name for each chain.
 - Add an RMF Viewer tool to allow the RMF hierarchy to be explored.

0.1 - 2020-02-19
================
 - First release, with basic support for reading the coordinates
   of the first frame and 2-particle restraints (such as
   crosslinks) from RMF files.
