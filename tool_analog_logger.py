#!/usr/bin/env python3
"""
Serial proxy for JARVIS-TriggerFirmware analog logging.

Sits between the Arduino and the JARVIS acquisition tool. Opens the real
serial port, creates a virtual serial port (PTY), filters TYPE_ANALOG
messages into a CSV file, and forwards everything else transparently.

    Arduino UNO --USB--> This Proxy --PTY--> Acquisition Tool
                            |
                            +--> analog_log.csv

Requirements:
    pip install pyserial cobs

Usage:
    python tool_analog_logger.py --port /dev/ttyACM0 --output analog_log.csv

Then point the acquisition tool at the PTY path printed on startup
(or use the symlink at /tmp/jarvis_serial).
"""

import argparse
import csv
import os
import select
import signal
import struct
import time

import serial
from cobs import cobs

BAUDRATE = 115200
TYPE_SETUP = 1
TYPE_ANALOG = 6
PTY_SYMLINK = "/tmp/jarvis_serial"


def build_stop_command():
    """Build a COBS-encoded setup message with pulse_hz=0 to stop the Arduino."""
    # Legacy setup: header(3) + pulse_hz(1) + pulse_limit(4) + delay_us(4) + flags(1)
    payload = struct.pack("<BIIB", 0, 0, 0, 0)  # pulse_hz, pulse_limit, delay_us, flags
    crc = sum(payload) & 0xFF
    header = struct.pack("<BBB", TYPE_SETUP, len(payload), crc)
    raw = header + payload
    return cobs.encode(raw) + b"\x00"


def main():
    parser = argparse.ArgumentParser(
        description="JARVIS Analog Proxy - filters analog data to CSV, "
        "forwards all other traffic to the acquisition tool via PTY"
    )
    parser.add_argument(
        "--port",
        required=True,
        help="Serial port of the Arduino (e.g., /dev/ttyACM0)",
    )
    parser.add_argument(
        "--output",
        default="analog_log.csv",
        help="Output CSV file (default: analog_log.csv)",
    )
    parser.add_argument(
        "--symlink",
        default=PTY_SYMLINK,
        help=f"Path for PTY symlink (default: {PTY_SYMLINK})",
    )
    args = parser.parse_args()

    # Create PTY pair
    master_fd, slave_fd = os.openpty()
    slave_name = os.ttyname(slave_fd)

    # Create symlink for easy access
    if os.path.exists(args.symlink) or os.path.islink(args.symlink):
        os.remove(args.symlink)
    os.symlink(slave_name, args.symlink)

    # Open real serial port (this resets the Arduino via DTR)
    ser = serial.Serial(port=args.port, baudrate=BAUDRATE, timeout=0)
    time.sleep(2)  # Wait for Arduino reset
    ser.reset_input_buffer()

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

        print(f"Proxy started:")
        print(f"  Arduino port: {args.port}")
        print(f"  PTY device:   {slave_name}")
        print(f"  Symlink:      {args.symlink}")
        print(f"  CSV output:   {args.output}")
        print()
        print(f"Point the acquisition tool at: {args.symlink}")
        print(f"Press Ctrl+C to stop.")

        pty_listening = True  # Whether to include PTY in select()

        while running:
            # Build list of file descriptors to monitor
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
                        arduino_buf = arduino_buf[idx + 1 :]

                        if not frame:
                            continue

                        # Decode COBS to inspect message type
                        try:
                            decoded = cobs.decode(frame)
                        except cobs.DecodeError:
                            # Forward malformed frames as-is
                            try:
                                os.write(master_fd, frame + b"\x00")
                            except OSError:
                                pass
                            continue

                        if len(decoded) >= 1 and decoded[0] == TYPE_ANALOG:
                            # Parse analog message: header(3) + payload(10)
                            # header: type(1) + length(1) + crc(1)
                            # payload: analog_value(u16) + uptime_us(u32) + pulse_id(u32)
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
                            # Acquisition tool disconnected — stop Arduino
                            print("\nAcquisition tool disconnected, stopping Arduino...")
                            try:
                                ser.write(build_stop_command())
                                ser.flush()
                            except serial.SerialException:
                                pass
                            acq_tool_was_connected = False
                        # Stop selecting on PTY until acq tool reconnects
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


    # Send stop command to Arduino so it stops pulsing/streaming
    print("\nSending stop command to Arduino...")
    try:
        ser.write(build_stop_command())
        ser.flush()
        time.sleep(0.1)
    except serial.SerialException:
        pass

    # Cleanup
    ser.close()
    os.close(master_fd)
    os.close(slave_fd)
    if os.path.islink(args.symlink):
        os.remove(args.symlink)

    print(f"Done. {sample_count} analog samples logged to {args.output}")


if __name__ == "__main__":
    main()
