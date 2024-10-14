#!/usr/bin/env bash
sudo apt-get install -y python3.11-venv
python3 -m venv .venv
. .venv/bin/activate
pip3 install -r requirements.txt
python3 -m PyInstaller --onefile --paths src --hidden-import="googleapiclient" main.py
tar -czvf dist/archive.tar.gz dist/main
