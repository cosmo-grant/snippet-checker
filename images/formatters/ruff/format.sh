#!/bin/sh
set -eu
ruff format /tmp/input
mv /tmp/input /tmp/output
