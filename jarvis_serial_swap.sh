#!/bin/bash
# Helper script for JARVIS analog proxy.
# Swaps /dev/ttyACM0 between the real Arduino device and a PTY.
# Called via sudo by tool_analog_logger.py.

set -e

case "$1" in
    swap)
        # Replace /dev/ttyACM0 with a symlink to the PTY
        if [ -z "$2" ]; then
            echo "Usage: $0 swap <pty_path>" >&2
            exit 1
        fi
        rm -f /dev/ttyACM0
        ln -s "$2" /dev/ttyACM0
        ;;
    restore)
        # Restore /dev/ttyACM0 as a symlink to /dev/ttyJARVIS
        rm -f /dev/ttyACM0
        ln -s /dev/ttyJARVIS /dev/ttyACM0
        ;;
    *)
        echo "Usage: $0 {swap <pty_path>|restore}" >&2
        exit 1
        ;;
esac
