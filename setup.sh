#!/bin/bash
. /etc/bash_completion

sudo apt install -y ethtool python-tk gdb-arm-none-eabi
mkvirtualenv halucinator
workon halucinator
#git submodule update --init

#Need to upstream my changes
git clone https://github.com/avatartwo/avatar2.git 3rd_party/avatar2

pip install -e 3rd_party/avatar2

# Avatar broke emulate capability which halucinator uses,
# Use old commit until fixed
pushd 3rd_party/avatar2
git checkout c43d08f10b8fdc662d0cc66e4b3bd2d272c8c9ba
popd

pip install -r src/requirements.txt
pip install -e src

echo "If you haven't already build avatar-qemu you will need to do so"
echo "   cd 3rd_party"
echo "   ./build_qemu.sh"


# May also need to install angr

# git clone https://github.com/angr/angr-dev.git
# cd angr-dev
# ./setup.sh -i -e angr
# workon angr
# pip install pyyaml