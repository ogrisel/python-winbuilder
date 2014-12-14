python-winbuilder
=================

Tool to setup a build environment on Windows for Python projects with compiled
extensions using Carl Kleffner's [MinGW static compiler toolchain](
https://bitbucket.org/carlkl/mingw-w64-for-python/downloads).

This project can be used in the following contexts:

- setting up a build environment under Windows for [AppVeyor CI](
  http://appveyor.com),
- setting up a build environment under Linux & Wine for [Travis CI](
  http://travis-ci.org),
- setting up a docker-based Linux + Wine local build and debug environment.


Operations
----------

Here is the sequence of operations that are automated by the `pywinbuilder`
tool:

1. Install Python using the official `.msi` installers of Python.org if needed,
2. Install pip using [get-pip.py](https://bootstrap.pypa.io/get-pip.py),
3. Download and extract the `mingw-w64-for-python` archive,
4. Generate the `libpythonXX.dll.a` and install it in the Python `libs` folder,
5. Copy `libmsvcr90.a` or `libmsvr100.a` into the Python `libs` folder,
6. Enable the correct `specs` file for `mingw` depending on the Python version,
7. Select `mingw` as the default compiler in `distutils.cfg`
8. Install a workaround for [issue 4709](https://bugs.python.org/issue4709)
   in `distutils.cfg` (Python 2.7 64 bit only).


Install
-------

As usual:

    pip install python-winbuilder

Alternatively you can just download the [pywinbuilder.py](pywinbuilder.py)
script and replace `python -m pywinbuilder` with `python pywinbuilder.py` in
the following usage examples.


Windows usage
-------------

    SET PYTHON_HOME=C:\Python34-x64
    SET PYTHON_VERSION=3.4.2
    SET ARCH=64
    SET MINGW_HOME=C:\mingw-static
    python -m pywinbuilder

Then you can activate the build environment matching this configuration by
changing the `PATH` environment variable and proceeding with building and
testing your own code as usual:

    set PATH=%PYTHON_HOME%;%PYTHON_HOME%\\Scripts;%MINGW_HOME%\\bin;%PATH%
    cd my-python-project
    python setup.py build_ext -i
    pip install nose
    nosetests .

See the [appveyor.yml](appveyor.yml) for a more complete example.


Linux usage
-----------

This requires wine 1.6+:

   export PYTHON_HOME="C:\\Python34-x64"
   export PYTHON_VERSION="3.4.2"
   export ARCH="64"
   export MINGW_HOME="C:\\mingw-static"
   python -m pywinbuilder

See the [.travis.yml](.travis.yml) for a more complete example.

It is also possible to pass a custom `WINEPREFIX` environment variable to
isolate several build environment for different versions of Python and
architectures on the same host.


Docker usage
------------

You can use [docker](http://www.docker.com) to run a Linux container with Wine
and mingw-based build environments for many versions of Python at once. Run a
new interactive session with:

    docker run -t -i -v ~/code:/code ogrisel/python-winbuilder bash

Note that this is mounting the `~/code` folder of your host operating system
into the `/code` folder of your container. This makes it possible to access
the source code of the project you want to build.

In that session you can use:

    WINEPREFIX=/wine/wine-py2.7.8-64 wineconsole --backend=curses cmd

to launch an interactive Windows `cmd` session for a given version of Python
and architecture. In that session you can build and test your code as you would
do under Windows.

    cd Z:\code\my-project
    python -m pip install -f requirements.txt
    python setup.py build_ext -i

    python -m pip install nose
    nosetests .

Use `exit` to end the `cmd` session.

Note the use of `python -m pip install` instead of the usual `pip install`
command that does not seem to work under Wine for some unknown reason.

See the [pywinbuilder.yml](pywinbuilder.yml) configuration file for the list of
available Python versions.

You can rebuild the container with:

    docker build -t ogrisel/python-winbuilder .

[Dockerfile](Dockerfile) for the details on how this container is configured.
