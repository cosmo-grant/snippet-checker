#!/bin/sh
set -e
mv main main.rs
exec rustc main.rs
