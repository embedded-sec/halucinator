#!/bin/bash
# . /etc/bash_completion
# set -e 
set -x
sudo apt-get install -y ethtool python-tk gdb-arm-none-eabi tcpdump python3-pip python3-venv cmake g++ build-essential

VIRT_ENV="halucinator"
AVATAR_REPO=https://github.com/avatartwo/avatar2.git
# Avatar broke emulated memory capability which halucinator requires,
# Use old commit until fixed

CREATE_VIRT_ENV=true


sudo apt-get install y python3-pip
sudo pip3 install virtualenv virtualenvwrapper
python3 -m venv ~/.virtualenv/"$VIRT_ENV"


# Activate the virtual environment (workon doesn't work in the script)
source ~/.virtualenv/$VIRT_ENV/bin/activate
