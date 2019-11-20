#!/bin/bash
# . /etc/bash_completion
# set -e 

AVATAR_COMMIT=c43d08f10b8fdc662d0cc66e4b3bd2d272c8c9ba
set -x

# If avatar already cloned just pull
if pushd deps/avatar2; then
    git pull
    popd
else
    git clone  "$AVATAR_REPO" deps/avatar2    
fi

# keystone-engine is a dependency of avatar, but pip install doesn't build
# the shared library. So build if from the repo
pip install --no-cache-dir --no-binary keystone-engine keystone-engine




# Avatar broke memory emulate capability which halucinator uses,
# Use old commit until fixed
pushd deps/avatar2
git checkout "$AVATAR_COMMIT"
pip install -e .

#Get submodules of avatar and build qemu
git submodule update --init --recursive


pushd targets
./build_qemu.sh
#./build_panda.sh
popd
popd

# Install halucinator dependencies
pip install -r src/requirements.txt
pip install -e src

