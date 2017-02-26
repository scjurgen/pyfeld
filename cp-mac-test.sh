#!/usr/bin/env bash

python -m compileall pyfeld
sudo cp -R pyfeld/* /usr/local/lib/python3.4/site-packages/pyfeld/
sudo chmod -R 0644 /usr/local/lib/python3.4/site-packages/pyfeld/*

sudo cp -R pyfeld/* /usr/local/lib/python2.7/site-packages/pyfeld/
sudo chmod -R 0644 /usr/local/lib/python2.7/site-packages/pyfeld/*
