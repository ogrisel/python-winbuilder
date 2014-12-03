# Build with:
# docker build -t ogrisel/python-winbuilder .
FROM ubuntu:trusty
MAINTAINER Olivier Grisel <olivier.grisel@ensta.org>

RUN dpkg --add-architecture i386
RUN apt-get update -y -qq
RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:fkrull/deadsnakes
RUN apt-get update -y -qq
RUN apt-get install -y python2.7-dev python3.3-dev python3.4-dev
RUN apt-get install wget
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python2.7 get-pip.py
RUN python3.3 get-pip.py

RUN python3.4 get-pip.py
RUN python3.4 -m pip install pyyaml

RUN apt-get install -y wine

ADD scripts/setup_wine_env.py setup_wine_env.py
ADD python_winbuilder.yml python_winbuilder.yml
RUN python3.4 setup_wine_env.py python_winbuilder.yml
