#!/usr/bin/env bash

# --- Configuration ---
# Extra tabs and directories
TAB1_DIR="$HOME/projects/02-fintools/bucket-ledger/git/windfall-ledger"
TAB1_TITLE="WLedger"

TAB2_DIR="$HOME/projects/02-fintools/bucket-ledger/git/terry-ledger"
TAB2_TITLE="TLedger"

# --- Helper Function ---
# Ptyxis doesn't have a direct '--title' flag per tab from the CLI,
# so we inject set an env var and modified our ~/.bashrc file to apply it
launch_tab() {
    local title="$1"
    local dir="$2"

    # Clean, production-ready execution command
    ptyxis --tab --working-directory="$dir" -- \
      bash -c "export TARGET_TAB_TITLE='$title'; exec bash" &

    sleep 0.15
}

# --- Main Execution ---
# Check if ptyxis is installed
if ! command -v ptyxis &> /dev/null; then
    echo "Error: ptyxis could not be found. Please install it or verify your PATH."
    exit 1
fi

# Build and launch the ptyxis layout
ptyxis $(launch_tab "$TAB1_TITLE" "$TAB1_DIR") \
       $(launch_tab "$TAB2_TITLE" "$TAB2_DIR") &

# Disown the process so it keeps running if you close the spawning terminal
disown
