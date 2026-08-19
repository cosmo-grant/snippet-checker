#!/bin/sh
set -e
mv main main.go
exec go build main.go
