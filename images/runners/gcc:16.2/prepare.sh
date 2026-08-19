#!/bin/sh
set -e
mv main main.c
exec gcc -o main main.c
