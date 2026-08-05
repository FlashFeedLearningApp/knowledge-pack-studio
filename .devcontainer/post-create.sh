#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

tool_root=".tools/image-sourcery"
tool_revision="5fc6ce4da1ca6ba869abc065a9495b5f6c92b73b"
if [[ ! -d "${tool_root}/.git" ]]; then
  git clone --filter=blob:none https://github.com/garygeo-19/image-sourcery.git "${tool_root}"
fi
git -C "${tool_root}" fetch --depth 1 origin "${tool_revision}"
git -C "${tool_root}" checkout --detach "${tool_revision}"
npm --prefix "${tool_root}" ci
npm --prefix "${tool_root}" run build

echo "Knowledge Pack Studio is ready. Open notebooks/Knowledge_Pack_Studio_v2.ipynb."
