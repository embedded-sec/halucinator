#!/bin/bash
# . /etc/bash_completion
set -e 
set -

AVATAR_REPO=https://github.com/avatartwo/avatar2.git
# AVATAR_COMMIT=c43d08f10b8fdc662d0cc66e4b3bd2d272c8c9ba


# If avatar already cloned just pull
if pushd deps/avatar2; then
    git pull
    popd
else
    git clone  "$AVATAR_REPO" deps/avatar2    
fi

# keystone-engine is a dependency of avatar, but pip install doesn't build
# correctly on ubuntu
# use angr's prebuilt wheel
pip install https://github.com/angr/wheels/raw/master/keystone_engine-0.9.1.post3-py2.py3-none-linux_x86_64.whl

#Get submodules of avatar and build qemu
git submodule update --init --recursive


# Avatar broke memory emulate capability which halucinator uses,
# Use old commit until fixed
pushd deps/avatar2
# git checkout "$AVATAR_COMMIT"
pip install -e .

pushd targets
./build_qemu.sh
#./build_panda.sh
popd
popd

# Install halucinator dependencies
pip install -r src/requirements.txt
pip install -e src

