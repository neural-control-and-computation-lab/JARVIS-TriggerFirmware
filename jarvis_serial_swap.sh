#!/bin/bash
# Helper script for JARVIS analog proxy.
# Uses bind mount to overlay /dev/ttyACM0 with a PTY.
# Called via sudo by tool_analog_logger.py.

case "$1" in
    swap)
        if [ -z "$2" ]; then
            echo "Usage: $0 swap <pty_path>" >&2
            exit 1
        fi
        mount --bind "$2" /dev/ttyACM0
        ;;
    restore)
        # Use lazy unmount to handle busy mount points (e.g. if the
        # acquisition tool hasn't fully released the fd yet)
        umount -l /dev/ttyACM0 2>/dev/null || true
        ;;
    *)
        echo "Usage: $0 {swap <pty_path>|restore}" >&2
        exit 1
        ;;
esac
