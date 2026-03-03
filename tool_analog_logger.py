#!/usr/bin/env python3
"""
Serial proxy for JARVIS-TriggerFirmware analog logging.

Sits between the Arduino and the JARVIS acquisition tool. Opens the real
Arduino serial device (/dev/ttyJARVIS), creates a PTY, and swaps
/dev/ttyACM0 to point to the PTY so the acquisition tool connects through
the proxy transparently. TYPE_ANALOG messages are filtered to CSV;
everything else is forwarded unchanged.

    Arduino (/dev/ttyJARVIS) --> Proxy --> /dev/ttyACM0 (PTY) --> Acquisition Tool
                                  |
                                  +--> analog_log.csv

Prerequisites (installed automatically by install_arduino_uno.sh):
    - udev rule creating /dev/ttyJARVIS
    - jarvis_serial_swap helper in /usr/local/bin
    - sudoers entry for jarvis_serial_swap
    - pip install pyserial cobs

Usage:
    python tool_analog_logger.py --output analog_log.csv

Then start the acquisition tool as normal (it connects to /dev/ttyACM0).
"""

import argparse
import csv
import os
import select
import signal
import struct
import subprocess
import time
import tty

import serial
from cobs import cobs

BAUDRATE = 115200
TYPE_SETUP = 1
TYPE_ANALOG = 6
SWAP_HELPER = "/usr/local/bin/jarvis_serial_swap"
DEFAULT_PORT = "/dev/ttyJARVIS"


def build_stop_command():
    """Build a COBS-encoded setup message with pulse_hz=0 to stop the Arduino."""
    # Legacy setup: header(3) + pulse_hz(1) + pulse_limit(4) + delay_us(4) + flags(1)
    payload = struct.pack("<BIIB", 0, 0, 0, 0)
    crc = sum(payload) & 0xFF
    header = struct.pack("<BBB", TYPE_SETUP, len(payload), crc)
    raw = header + payload
    return cobs.encode(raw) + b"\x00"


def swap_ttyACM0(pty_path):
    """Replace /dev/ttyACM0 with a symlink to the PTY."""
    try:
        subprocess.run(
            ["sudo", SWAP_HELPER, "swap", pty_path],
            check=True, timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Warning: Could not swap /dev/ttyACM0: {e}")
        return False


def restore_ttyACM0():
    """Restore /dev/ttyACM0 to point to the real Arduino device."""
    try:
        subprocess.run(
            ["sudo", SWAP_HELPER, "restore"],
            check=True, timeout=5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("Warning: Could not restore /dev/ttyACM0. Unplug and replug the Arduino.")


def main():
    parser = argparse.ArgumentParser(
        description="JARVIS Analog Proxy - transparently intercepts analog "
        "data from the Arduino and logs it to CSV while the acquisition "
        "tool operates normally."
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=f"Serial port of the Arduino (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--output",
        default="analog_log.csv",
        help="Output CSV file (default: analog_log.csv)",
    )
    args = parser.parse_args()

    # Clean up any stale bind mount from a previous run
    restore_ttyACM0()

    # Verify the Arduino device exists
    if not os.path.exists(args.port):
        print(f"Error: {args.port} not found.")
        if args.port == DEFAULT_PORT:
            print("Make sure the Arduino is plugged in and the udev rule is installed.")
            print("Run 'sh install_arduino_uno.sh' to set up, then unplug/replug the Arduino.")
        return 1

    # Create PTY pair and set to raw mode
    master_fd, slave_fd = os.openpty()
    tty.setraw(master_fd)
    tty.setraw(slave_fd)
    slave_name = os.ttyname(slave_fd)

    # Open real serial port (this resets the Arduino via DTR)
    print(f"Opening Arduino on {args.port}...")
    ser = serial.Serial(port=args.port, baudrate=BAUDRATE, timeout=0)
    time.sleep(2)  # Wait for Arduino reset
    ser.reset_input_buffer()

    # Swap /dev/ttyACM0 to point to our PTY
    print(f"Redirecting /dev/ttyACM0 -> {slave_name}...")
    swapped = swap_ttyACM0(slave_name)
    if not swapped:
        print("Falling back: acquisition tool must connect to /tmp/jarvis_serial")
        # Create fallback symlink
        fallback = "/tmp/jarvis_serial"
        if os.path.exists(fallback) or os.path.islink(fallback):
            os.remove(fallback)
        os.symlink(slave_name, fallback)

    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    sample_count = 0
    rate_window_start = time.time()
    rate_window_count = 0

    # Buffer for accumulating bytes from Arduino
    arduino_buf = bytearray()

    # Track whether acquisition tool has connected/disconnected
    acq_tool_was_connected = False

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp_us", "pulse_id", "analog_value"])

        print()
        print(f"Proxy ready. Analog data -> {args.output}")
        print(f"Start the acquisition tool normally. Press Ctrl+C to stop.")

        pty_listening = True

        while running:
            read_fds = [ser.fileno()]
            if pty_listening:
                read_fds.append(master_fd)

            try:
                readable, _, _ = select.select(read_fds, [], [], 0.1)
            except (ValueError, OSError):
                break

            for fd in readable:
                if fd == ser.fileno():
                    # Data from Arduino
                    try:
                        data = ser.read(ser.in_waiting or 1)
                    except serial.SerialException:
                        running = False
                        break
                    if not data:
                        continue

                    arduino_buf.extend(data)

                    # Process complete COBS frames (delimited by 0x00)
                    while b"\x00" in arduino_buf:
                        idx = arduino_buf.index(b"\x00")
                        frame = bytes(arduino_buf[:idx])
                        arduino_buf = arduino_buf[idx + 1:]

                        if not frame:
                            continue

                        # Decode COBS to inspect message type
                        try:
                            decoded = cobs.decode(frame)
                        except cobs.DecodeError:
                            try:
                                os.write(master_fd, frame + b"\x00")
                            except OSError:
                                pass
                            continue

                        if len(decoded) >= 1 and decoded[0] == TYPE_ANALOG:
                            # Parse analog payload after 3-byte header:
                            #   analog_value(u16) + uptime_us(u32) + pulse_id(u32)
                            if len(decoded) >= 13:
                                analog_value, uptime_us, pulse_id = struct.unpack_from(
                                    "<HIL", decoded, 3
                                )
                                writer.writerow(
                                    [uptime_us, pulse_id, analog_value]
                                )
                                sample_count += 1
                                rate_window_count += 1

                                if sample_count % 100 == 0:
                                    csvfile.flush()
                                    now = time.time()
                                    window = now - rate_window_start
                                    rate = (
                                        rate_window_count / window
                                        if window > 0
                                        else 0
                                    )
                                    rate_window_start = now
                                    rate_window_count = 0
                                    print(
                                        f"  {sample_count} analog samples, "
                                        f"{rate:.1f} samples/sec"
                                    )
                            # Do NOT forward TYPE_ANALOG to acquisition tool
                        else:
                            # Forward all other messages to acquisition tool
                            try:
                                os.write(master_fd, frame + b"\x00")
                            except OSError:
                                pass

                elif fd == master_fd:
                    # Data from acquisition tool -> forward to Arduino
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError:
                        if acq_tool_was_connected:
                            print("\nAcquisition tool disconnected, stopping Arduino...")
                            try:
                                ser.write(build_stop_command())
                                ser.flush()
                            except serial.SerialException:
                                pass
                            acq_tool_was_connected = False
                        pty_listening = False
                        continue
                    if data:
                        acq_tool_was_connected = True
                        pty_listening = True
                        try:
                            ser.write(data)
                        except serial.SerialException:
                            running = False
                            break

    # Send stop command to Arduino
    print("\nSending stop command to Arduino...")
    try:
        ser.write(build_stop_command())
        ser.flush()
        time.sleep(0.1)
    except serial.SerialException:
        pass

    # Close all file descriptors first, then unmount
    ser.close()
    os.close(master_fd)
    os.close(slave_fd)

    if swapped:
        print("Restoring /dev/ttyACM0...")
        restore_ttyACM0()

    # Remove fallback symlink if it exists
    fallback = "/tmp/jarvis_serial"
    if os.path.islink(fallback):
        os.remove(fallback)

    print(f"Done. {sample_count} analog samples logged to {args.output}")


if __name__ == "__main__":
    main()
