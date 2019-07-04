
# Halucinator Setup

This document was contributed by [Teserakt AG](https://teserakt.io) 
in order to allow new developers to get started hacking on halucinator. 

## Dependencies

 * Python 3
 * virtualenv
 * virtualenvwrapper (workon)
 * angr (binary analysis framework)
 * avatar2's qemu backend, see [github](https://github.com/avatartwo/avatar-qemu) and 
   [avatar2](https://github.com/avatartwo/avatar2).
 * pycparser, v2.18,  BSD,   https://github.com/eliben/pycparser
 * angr
 * 0MQ
 * python-tk
 * ethtool
 * keystone (because the python bindings don't build it)

## Setup / build instructions

 1. Make sure you have all submodules; run:

        git submodule update --init --recursive

    in the root of the repository.

 1. Set up your python environment. HALucinator uses virtualenvwrapper and 
    this takes some additional work to install. Firstly:

        pip install --user --upgrade --ignore-installed virtualenvwrapper

    Your pip command may change depending on your platform and python 
    interpreter. For example, fedora uses pip3 for python3.

    Installing commands locally (rather than your system site-packages) 
    prevents you from screwing up your distribution's versioning (yes, 
    python's distribution "story" sucks). This is why we are doing this.

    To make any "bin" output from such installs available, include these 
    in your shell's rc scripts:

        export PY2_USER_BIN=$(python -c 'import site; print(site.USER_BASE + "/bin")')
        export PY3_USER_BIN=$(python3 -c 'import site; print(site.USER_BASE + "/bin")')
        export PATH=$PATH:$PY2_USER_BIN:$PY3_USER_BIN

    again, this may need adjustment for your system. Fedora runs both python3/
    python2 side by side; not all Linuxes do. I have no idea what Mac does.

    Reload your shell's environment using something like

        source ~/.bashrc

    Now you can load virtualenvwrapper as follows:

        source virtualenvwrapper.sh

    and you can now use virtualenvwrapper to enter an environment for HAL:

        mkvirtualenv halucinator

 1. Install HALucinator's dependencies as follows:


        workon halucinator

    if you have not already, then:

        pip install deps/avatar2/
        pip install -r src/requirements.txt
        pip install src/
 

 1. Build keystone as follows:

    First, make a build directory and enter it:

        mkdir deps/keystone/build
        pushd deps/keystone/build

    Next, run cmake to build locally:

        cmake -DBUILD_SHARED_LIBS=ON -G "Unix Makefiles" ../
        
    You can install capstone system-wide on Redhat systems as follows:

        cmake -DCMAKE_INSTALL_PREFIX="/usr/local/" -DLLVM_LIBDIR_SUFFIX=64 -DBUILD_SHARED_LIBS=ON -G "Unix Makefiles" ../

    Now once either of these commands completes, build the library:

        make -j8

    If you configured it to install, use:

        sudo make install

    Otherwise you can copy the libkeystone shared object into your local keystone 
    installation. **You need to do this with virtualenv activated**. Then do:

        SITEPKG=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")
        cp -v ./llvm/lib64/libkeystone.so $(SITEPKG)/keystone/

    this works as keystone python bindings search there.

 1. Build avatar-qemu:

        cd avatar-qemu
        ./configure --disable-sdl --target-list=arm-softmmu
        make -j8

 1. You should now be ready to run HALucinator. See [running](running.md). 
