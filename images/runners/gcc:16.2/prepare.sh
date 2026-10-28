#!/bin/sh
set -e
mv main main.c
# Try to catch undefined behaviour.
exec gcc \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    -Werror=uninitialized -Werror=sequence-point \
    -o main main.c
