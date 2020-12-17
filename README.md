[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3675794.svg)](https://doi.org/10.5281/zenodo.3675794)
[![Linux Build Status](https://github.com/salilab/rmf_chimerax/workflows/build/badge.svg?branch=chimerax_1.2)](https://github.com/salilab/rmf_chimerax/actions?query=workflow%3Abuild)
[![Windows Build status](https://ci.appveyor.com/api/projects/status/mq3gpl2t8jd8s8yb?svg=true)](https://ci.appveyor.com/project/benmwebb/rmf-chimerax)
[![codecov](https://codecov.io/gh/salilab/rmf_chimerax/branch/master/graph/badge.svg)](https://codecov.io/gh/salilab/rmf_chimerax)

This is an experimental ChimeraX plugin to read and visualize
[RMF](https://integrativemodeling.org/rmf/) files, used primarily by the
[Integrative Modeling Platform (IMP)](https://integrativemodeling.org/).

Currently it will:
 - read and display all frames from an RMF file
 - display 2-particle restraints (such as cross-links)
 - display RMF geometry, such as bounding boxes
 - show provenance (information about how the model was generated, including
   external files such as electron microscopy density maps or input
   PDB files)

Residues in read-in RMF files are given the following attributes which can
be used in ChimeraX selections (see `help select` from the ChimeraX command
line):

 - `rmf_name`: The name of the containing molecule
 - `copy`: The (integer) copy number, usually 0 or unspecified for the
   primary copy of a molecule
 - `resolution`: The IMP/PMI resolution of the representation, usually 0 for
   atomic, 1 for a single bead per residue, 10 or more for multiple residues per
   bead

For example, all of the non-primary copies could be selected with
`select ::copy>0` or only the bead-per-residue representation of the primary
copy of Tub0 could be selected with
`select ::rmf_name="Tub0" & ::copy=0 & ::resolution=1`.

An `rmf` command is also added to ChimeraX, which if run will show
the RMF hierarchy or chain names in the log, or read additional frames
from the RMF file. Use `help rmf` from ChimeraX for more information.

An RMF Viewer tool is also added to ChimeraX, which allows the RMF hierarchy,
features and provenance to be explored.

## Installation

Stable releases can be installed directly from ChimeraX using the
[ChimeraX Toolshed](https://cxtoolshed.rbvi.ucsf.edu/). (From the Tools menu,
select "More Tools" and then select the RMF plugin.)

The most recent code on GitHub can be used by cloning it, then running
`make install` to install the plugin in ChimeraX. This needs to know where
your copy of ChimeraX is installed, which you can do by setting the
`CHIMERAX_APP` environment variable to the directory containing ChimeraX (on
Windows or Mac) or `CHIMERAX_EXE` to the full path to the `chimerax` binary
(on Linux).

## Testing

This plugin has a full test suite which is designed to run in one of two
environments:

 - mock environment; this exercises all of the code with the major dependencies
   (PySide2, ChimeraX itself) mocked out. This is faster, does not require a
   display, and does not require PySide2 or ChimeraX to be available, but can
   potentially miss problems if the mock and ChimeraX APIs diverge. It can
   be run with `make test`. The tests can also be run against the real PySide2
   (this requires PySide2 to be installed, plus a display) with `make test-qt`.
 - ChimeraX; this runs the tests against ChimeraX itself, so requires ChimeraX
   to be installed. Currently this does not test any GUI components such as
   the RMF Viewer tool. It can be run with `make test-chimerax`.
