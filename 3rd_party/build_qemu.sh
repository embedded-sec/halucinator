#!/bin/bash
source /etc/os-release
set -e

# if [[ "$ID" == "ubuntu" ]]
# then
#   sudo bash -c 'echo "deb-src http://archive.ubuntu.com/ubuntu/ '$UBUNTU_CODENAME'-security main restricted" >> /etc/apt/sources.list'
#   sudo apt-get update
#   sudo apt-get build-dep -y qemu
# fi

# May need to update to different repo
if [[! -d "/path/to/dir"]]
then
    git clone https://github.com/avatartwo/avatar-qemu.git avatar-qemu
fi
cd avatar-qemu
git submodule update --init --recursive 

./configure --disable-sdl --target-list=arm-softmmu
make -j4

