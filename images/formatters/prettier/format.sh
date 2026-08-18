#!/bin/sh
set -eu
prettier --parser babel /tmp/input >/tmp/output
