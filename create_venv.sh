#!/bin/bash
# . /etc/bash_completion
set -e 
#set -x
sudo apt-get install -y ethtool python-tk gdb-arm-none-eabi tcpdump python3-pip python3-venv cmake g++ build-essential

VIRT_ENV="halucinator"

sudo pip3 install virtualenv virtualenvwrapper
python3 -m venv ~/.virtualenv/"$VIRT_ENV"

# Activate the virtual environment (workon doesn't work in the script)
echo "$VIRT_ENV virt environment created now run:" 
echo "source ~/.virtualenv/$VIRT_ENV/bin/activate"
echo "./setup.sh"
