#!/usr/bin/env bash

sudo rm -rf pyfeld.egg-infoA
sudo rm -rf dist
sudo rm -rf build
python setup.py build
python setup.py dist 
python setup.py sdist
python setup.py bdist_wheel
twine upload dist/*

