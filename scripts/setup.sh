#!/bin/sh

## Make sure we have everything in this repository
git submodule update --init --recursive

## Set up virtualenvwrapper if the user doesn't already have it
pip install --user --upgrade --ignore-installed virtualenvwrapper

## Don't mess with the user's env variables in this script;
## messing with user's environments for them is quite anti-social
if ! command -v mkvirtualenv &> /dev/null; then
    echo "Unable to locate your mkvirtualenv command; please add the following directories"
    echo "to your path:"
    PY_USER_BIN=$(python -c 'import site; print(site.USER_BASE + "/bin")')
    echo $PY_USER_BIN
    exit
fi

pushd deps/avatar-qemu
./configure --disable-sdl --target-list=arm-softmmu
make -j8
popd


mkvirtualenv halucinator
workon halucinator
pip install deps/avatar2
pip install -r src/requirements.txt
pip install src


### make keystone work:

mkdir deps/keystone/build
pushd deps/keystone/build
cmake -DBUILD_SHARED_LIBS=ON -G "Unix Makefiles" ../
make -j8
SITEPKG=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
cp -v ./llvm/lib64/libkeystone.so $(SITEPKG)/keystone/
popd

echo "[*] Done"
