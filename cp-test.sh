#!/usr/bin/env bash

python -m compileall pyfeld
path=/usr/lib/python3.5/site-packages/pyfeld/
sudo cp -r pyfeld/* ${path} 
sudo chmod -R 0644 ${path}*
