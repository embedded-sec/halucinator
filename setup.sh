#!/bin/bash
. /etc/bash_completion
set -e 
set -x
sudo apt install -y ethtool python-tk gdb-multiarch tcpdump

VIRT_ENV="halucinator"
AVATAR_REPO=https://github.com/avatartwo/avatar2.git
# Avatar broke emulated memory capability which halucinator requires,
# Use old commit until fixed
# AVATAR_COMMIT=c43d08f10b8fdc662d0cc66e4b3bd2d272c8c9ba
CREATE_VIRT_ENV=true

#Look for flags and override
while [ -n "$1" ]; do
 case "$1" in
 -e)
    VIRT_ENV="$2"
    echo "Using Virtual Environment $2"
    shift
    ;;
 -r)
    AVATAR_REPO="$2"
    AVATAR_COMMIT="HEAD"
    echo "Using Avatar Repo $2"
    shift
    ;;
 -nc)
    CREATE_VIRT_ENV=false
    ;;
  * ) echo "Option $1 not recognized";;
 esac
 shift
done


if [ "$CREATE_VIRT_ENV" = true ]; then
   echo "Created Virtual Environment $VIRT_ENV"
   mkvirtualenv -p `which python3` "$VIRT_ENV"
fi

# Activate the virtual environment ('workon' doesn't work in the script)
source "$WORKON_HOME/$VIRT_ENV/bin/activate"


# If avatar already cloned just pull
if pushd deps/avatar2; then
    git pull
    popd
else
    git clone  "$AVATAR_REPO" deps/avatar2    
fi

# keystone-engine is a dependency of avatar, but pip install doesn't build
# correctly on ubuntu use angr's prebuilt wheel
pip install https://github.com/angr/wheels/raw/master/keystone_engine-0.9.1.post3-py2.py3-none-linux_x86_64.whl

pushd deps/avatar2

#Get submodules of avatar and build qemu
git submodule update --init --recursive
pip install -e .

pushd targets
./build_qemu.sh
#./build_panda.sh
popd
popd

# Install halucinator dependencies
pip install -r src/requirements.txt
pip install -e src
