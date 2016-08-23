#!/usr/bin/env bash

python -m compileall pyfeld
sudo cp -r pyfeld/* /usr/lib/python3.4/site-packages/pyfeld/
sudo chmod -R 0644 /usr/lib/python3.4/site-packages/pyfeld/*
