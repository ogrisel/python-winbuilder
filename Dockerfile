# Build with:
# docker build -t ogrisel/python-winbuilder .
FROM ubuntu:trusty
MAINTAINER Olivier Grisel <olivier.grisel@ensta.org>

WORKDIR /root
USER root

# Install wine with 32 bit support
RUN dpkg --add-architecture i386
RUN apt-get update -y -qq && apt-get install -y wine

# Install python 3.4 and pyyaml to run the main setup script
RUN apt-get install -y python3.4 curl
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.4
RUN python3.4 -m pip install pyyaml

# Prefetch mingw and Python to leverage Dockerfile caching
RUN curl -O -J -L https://bitbucket.org/carlkl/mingw-w64-for-python/downloads/mingw32static-2014-11.tar.xz
RUN curl -O -J -L https://bitbucket.org/carlkl/mingw-w64-for-python/downloads/mingw64static-2014-11.tar.xz

# Build the wine-based build environments
ADD pywinbuilder.py /root/pywinbuilder.py
ADD pywinbuilder.yml /root/pywinbuilder.yml
RUN python3.4 pywinbuilder.py pywinbuilder.yml

# Convenience: enable last wine prefix as the default
RUN ln -s /wine/wine-py3.4.2-64 $HOME/.wine
