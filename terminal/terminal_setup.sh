#!/usr/bin/env bash

# ##############################################################################
# Workspace Terminal Launcher
#
# Description:
#   Automates the creation of a customized, multi-tab terminal workspace using
#   Ptyxis. It dynamically loops through a user-defined collection of target
#   directories and injects persistent, custom tab titles into each session.
#
# Bash Integration:
#   This script passes a 'TARGET_TAB_TITLE' environment variable to each new
#   tab. For titles to persist without being overwritten by the standard prompt,
#   your ~/.bashrc should intercept this variable and append it to PS1:
#
#   if [ -n "$TARGET_TAB_TITLE" ]; then
#       PS1="\[\e]2;\${TARGET_TAB_TITLE}\a\]\$PS1"
#   fi
#
# Configuration:
#   Add, remove, or modify workspaces directly in the associative array below
#   using the format: ["/path/to/target/dir"]="Desired Tab Title"
#
# ##############################################################################

# --- Configuration (Define as many tabs as you want here) ---
# Format: [working_directory]="Tab Title"
declare -A WORKSPACE_TABS=(
    ["$HOME/projects/02-fintools/bucket-ledger/git/windfall-ledger"]="WLedger"
    ["$HOME/projects/02-fintools/bucket-ledger/git/terry-ledger"]="TLedger"
    # To add more tabs in the future, just uncomment/add lines like these:
    # ["$HOME/projects/weather-match"]="Weather Match"
    # ["/tmp"]="Scratchpad"
)

# --- Core Launch Function ---
launch_tab() {
    local dir="$1"
    local title="$2"

    # Clean execution command passing the title directly into the environment
    ptyxis --tab --working-directory="$dir" -- \
      bash -c "export TARGET_TAB_TITLE='$title'; exec bash" &

    # Give the window manager a brief instant to register the tab
    sleep 0.15
}

# --- Main Execution ---
if ! command -v ptyxis &> /dev/null; then
    echo "Error: ptyxis could not be found."
    exit 1
fi

# Iterate through the associative array and spawn each tab dynamically
for dir in "${!WORKSPACE_TABS[@]}"; do
    title="${WORKSPACE_TABS[$dir]}"
    launch_tab "$dir" "$title"
done

# Cleanly detach the backgrounded terminal instances
disown -a
