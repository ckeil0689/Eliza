#!/bin/bash

set -e

if [ -d ./venv ]; then
  VENV=./venv/bin/
  PYTHON=${VENV}python3
else
  PYTHON=python3
fi

export VENV
export PYTHON
