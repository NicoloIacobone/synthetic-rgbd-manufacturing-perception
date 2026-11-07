#!/usr/bin/env bash
# Create the BlenderProc launcher env (.venv-bproc), separate from the analysis env (.venv), and
# apply our macOS patch (patches/blenderproc-2.8.0-macos-app-bundle.patch, after upstream PR #1231):
# on recent macOS the signed Blender.app bundle is read-only, which breaks BlenderProc's first run.
# Blender itself is downloaded on first use into the repo-local, gitignored blender/ folder:
#   .venv-bproc/bin/blenderproc quickstart --blender-install-path blender
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -m venv .venv-bproc
.venv-bproc/bin/pip install -q -r requirements-bproc.lock.txt
# Not "import blenderproc": it refuses to load outside "blenderproc run".
SITE=$(.venv-bproc/bin/python -c "import site; print(site.getsitepackages()[0])")
if [[ "$(uname)" == "Darwin" ]]; then
  P=patches/blenderproc-2.8.0-macos-app-bundle.patch
  # Look for the patch's marker: Apple's "patch -R --dry-run" reports success on an unpatched file.
  if grep -q "synthrgbd patch" "$SITE/blenderproc/python/utility/SetupUtility.py"; then
    echo "macOS patch already applied"
  else
    patch -d "$SITE" -p1 < "$P"     # fails loudly if it does not apply
  fi
fi
echo "BlenderProc ready: .venv-bproc/bin/blenderproc"
