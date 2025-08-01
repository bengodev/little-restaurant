#!/usr/bin/env bash
set -e
pip3 install -r requirements.txt
python3 manage.py collectstatic --noinput
python3 manage.py migrate