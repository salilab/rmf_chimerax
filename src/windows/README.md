To build on Windows:

 - Use a Windows 7 VM with Anaconda and Visual Studio 2015 installed
 - Download rmf-develop.zip from https://github.com/salilab/rmf/, and
   make rmf-1.0.zip containing everything in rmf-develop.zip except for the
   symlinks `doc/PymolPlugin.md`, `doc/VMDPlugin.md` and `tools/dev_tools/git`.
 - Get https://github.com/salilab/conda-recipes and modify `rmf/meta.yaml` so
   that `url` points to `rmf-1.0.zip`
 - Start a VS2015 command prompt
 - Build a conda package with `conda build --python=3.8 rmf`
 - Extract from the resulting `tar.bz2` the files
   `Library/lib/RMF.dll Lib/site-packages/_RMF*pyd Lib/site-packages/RMF*py`
 - Add any needed DLLs from conda (usually in `Library/bin`)
