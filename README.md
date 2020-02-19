[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3675794.svg)](https://doi.org/10.5281/zenodo.3675794)
[![Linux Build Status](https://travis-ci.org/salilab/rmf_chimerax.svg?branch=master)](https://travis-ci.org/salilab/rmf_chimerax)
[![Windows Build status](https://ci.appveyor.com/api/projects/status/mq3gpl2t8jd8s8yb?svg=true)](https://ci.appveyor.com/project/benmwebb/rmf-chimerax)
[![codecov](https://codecov.io/gh/salilab/rmf_chimerax/branch/master/graph/badge.svg)](https://codecov.io/gh/salilab/rmf_chimerax)

This is an experimental ChimeraX plugin to read and visualize
[RMF](https://integrativemodeling.org/rmf/) files, used primarily by the
[Integrative Modeling Platform (IMP)](https://integrativemodeling.org/).
Currently it will only read and display the first frame from an RMF file and any
2-particle restraints (such as cross-links) although the longer-term goal
is to offer the same functionality as the RMF viewer in legacy Chimera plus
support for newer RMF features, such as provenance.

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
