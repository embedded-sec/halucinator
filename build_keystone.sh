#! /bin/bash
set -e
set -x

#Make sure in virtual environment
: ${VIRTUAL_ENV:?Should be run from your halucinator virtual environment}

sudo apt install -y cmake
if pushd deps/keystone; then
    git pull
    popd
else
    git clone https://github.com/keystone-engine/keystone deps/keystone    
fi

mkdir -p deps/keystone/build
pushd deps/keystone/build
cmake -DBUILD_SHARED_LIBS=ON -G "Unix Makefiles" ../
make -j8

pip install keystone-engine

SITEPKG=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
cp -v ./llvm/lib/libkeystone.so "${SITEPKG}"/keystone/

popd


