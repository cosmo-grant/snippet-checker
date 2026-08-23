#!/bin/sh
set -e
exec prettier --parser babel ./input >./output
