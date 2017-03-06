#!/usr/bin/env bash

versionsetup=`grep "this_version =" setup.py | sed "s/^.*version = ['\"]\([0-9ab.]*\)['\"].*$/\\1/g"`
versionrfcmd=`grep "version =" pyfeld/rfcmd.py | sed "s/^.*version = ['\"]\([0-9ab.]*\)['\"].*$/\\1/g" `

echo rfcmd: ${versionrfcmd}
echo setup.py ${versionsetup}

if [ "$versionrfcmd" != "$versionsetup" ] 
then
	echo "The version are different, please update them before packing"
        sleep 2 
        vi pyfeld/rfcmd.py +19
        vi setup.py +20
	exit -1
fi

sudo rm -rf pyfeld.egg-info
sudo rm -rf dist
sudo rm -rf build
python setup.py build
python setup.py dist 
python setup.py sdist
#python setup.py bdist_wheel
twine upload dist/*

