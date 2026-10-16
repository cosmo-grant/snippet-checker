#!/bin/sh
set -e
cljfmt fix ./input
mv ./input ./output
