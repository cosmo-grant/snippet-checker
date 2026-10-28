#!/bin/sh
ASAN_OPTIONS=detect_leaks=0:color=never UBSAN_OPTIONS=color=never exec ./main
