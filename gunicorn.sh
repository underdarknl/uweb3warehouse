#/bin/bash
export PYTHONPATH=/opt/uweb3
gunicorn3 --bind 0.0.0.0:8002 'wsgi:application'
