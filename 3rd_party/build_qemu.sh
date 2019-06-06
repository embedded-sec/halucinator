#!/bin/bash
source /etc/os-release

# if [[ "$ID" == "ubuntu" ]]
# then
#   sudo bash -c 'echo "deb-src http://archive.ubuntu.com/ubuntu/ '$UBUNTU_CODENAME'-security main restricted" >> /etc/apt/sources.list'
#   sudo apt-get update
#   sudo apt-get build-dep -y qemu
# fi

# May need to update to different repo
git clone https://github.com/avatartwo/avatar-qemu.git avatar-qemu
cd avatar-qemu
git submodule update --init --recursive 

git checkout qemu-3.1
./configure --disable-sdl --target-list=arm-softmmu
make -j4

