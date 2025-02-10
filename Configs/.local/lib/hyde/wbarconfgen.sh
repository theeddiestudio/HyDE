#!/usr/bin/env bash

# read control file and initialize variables

scrDir="$(dirname "$(realpath "$0")")"
# shellcheck disable=SC1091
source "${scrDir}/globalcontrol.sh"
# shellcheck disable=SC2154

echo "DEPRECATION: This script will be removed in the future."
"${scrDir}/waybar.py" --update-icon-size --update-border-radius --generate-includes
