#!/bin/sh
set -e
ruff format ./input
mv ./input ./output
