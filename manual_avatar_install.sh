#!/bin/bash
. /etc/bash_completion
set -e 
set -x

AVATAR_REPO=https://github.com/avatartwo/avatar2.git

# If avatar already cloned just pull
if pushd deps/avatar2; then
    git pull
    popd
else
    git clone  "$AVATAR_REPO" deps/avatar2    
fi

# Setup avatar2
pushd deps/avatar2
git submodule update --init --recursive
pip install -e .

pushd targets
./build_qemu.sh
#./build_panda.sh
popd
popd

