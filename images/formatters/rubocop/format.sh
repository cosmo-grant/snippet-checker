#!/bin/sh
set -e
cp ./input ./rubocop_work.rb
# rubocop exit_codes:
#   0 = no/low-severity/autocorrected offenses
#   1 = some high-severity non-autocorrected offenses
#   2 = rubocop error
# https://docs.rubocop.org/rubocop/latest/usage/cli_reference.html#exit-codes
# Our contract is: exit non-zero just if rubocop error.
# So exit 2 if 2 else ignore.
exit_code=0
rubocop --autocorrect ./rubocop_work.rb || exit_code=$?
if [ $exit_code = 2 ]; then exit 2; fi
mv ./rubocop_work.rb ./output
