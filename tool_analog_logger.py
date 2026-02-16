#!/usr/bin/env python3
"""
Passive analog data logger for JARVIS-TriggerFirmware.

Listens on the serial port for analog messages that the firmware
automatically streams whenever camera trigger pulses are active,
and logs them to a CSV file.

The firmware streams analog data from pin A0 at a default rate of
100 Hz whenever pulse_hz > 0. No setup command is needed — just
start your acquisition as usual, then run this logger alongside it.

Requirements:
    pip install pyserial cobs

Usage:
    python tool_analog_logger.py --port /dev/ttyACM0 --output analog_log.csv
"""

import argparse
import csv
import signal
import struct
import sys
import time

import serial
from cobs import cobs

# Message types (must match serial_messages.h)
TYPE_ECHO = 0
TYPE_SETUP = 1
TYPE_INPUTS = 2
TYPE_ACK = 3
TYPE_TXT = 4
TYPE_ERROR = 5
TYPE_ANALOG = 6

HEADER_SIZE = 3
BAUDRATE = 115200


def calculate_crc(payload: bytes) -> int:
    """8-bit sum CRC matching firmware."""
    return sum(payload) & 0xFF


def parse_message(raw_frame):
    """Decode a COBS frame and parse the header + payload."""
    if len(raw_frame) < 2:
        return None, None
    encoded = raw_frame.rstrip(b"\x00")
    if not encoded:
        return None, None
    try:
        decoded = cobs.decode(encoded)
    except cobs.DecodeError:
        return None, None
    if len(decoded) < HEADER_SIZE:
        return None, None
    msg_type, length, crc_val = struct.unpack("<BBB", decoded[:HEADER_SIZE])
    payload = decoded[HEADER_SIZE:]
    if len(payload) != length:
        return None, None
    if calculate_crc(payload) != crc_val:
        return None, None
    return msg_type, payload


def parse_analog_payload(payload):
    """Parse analog message payload: analog_value(u16) + uptime_us(u32) + pulse_id(u32)."""
    if len(payload) != 10:
        return None
    analog_value, uptime_us, pulse_id = struct.unpack("<HIL", payload)
    return {
        "analog_value": analog_value,
        "uptime_us": uptime_us,
        "pulse_id": pulse_id,
    }


def main():
    parser = argparse.ArgumentParser(
        description="JARVIS Analog Logger - passively records analog data "
        "streamed by the firmware whenever camera pulses are active"
    )
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyACM0)")
    parser.add_argument("--output", default="analog_log.csv", help="Output CSV file (default: analog_log.csv)")
    parser.add_argument("--duration", type=float, default=0, help="Recording duration in seconds (0=unlimited)")
    args = parser.parse_args()

    ser = serial.Serial(port=args.port, baudrate=BAUDRATE, timeout=0.1)
    time.sleep(2)  # Wait for Arduino reset after serial open

    if not ser.is_open:
        print("Failed to open port")
        sys.exit(1)

    ser.reset_input_buffer()

    sample_count = 0
    start_time = time.time()

    running = True

    def signal_handler(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["timestamp_us", "pulse_id", "analog_value"])

        print(f"Listening on {args.port}, logging to {args.output}...")
        print("Analog data will appear when camera pulses are active. Ctrl+C to stop.")

        while running:
            raw = ser.read_until(b"\x00")
            if not raw:
                continue

            msg_type, payload = parse_message(raw)
            if msg_type is None:
                continue

            if msg_type == TYPE_ANALOG:
                parsed = parse_analog_payload(payload)
                if parsed:
                    writer.writerow([
                        parsed["uptime_us"],
                        parsed["pulse_id"],
                        parsed["analog_value"],
                    ])
                    sample_count += 1
                    if sample_count % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = sample_count / elapsed if elapsed > 0 else 0
                        print(f"  {sample_count} samples, {rate:.1f} samples/sec")

            elif msg_type == TYPE_ERROR:
                print(f"Error from device: {payload}")
            elif msg_type == TYPE_TXT:
                print(f"Text from device: {payload.decode('ascii', errors='replace')}")

            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                break

    print(f"\nDone. {sample_count} samples logged to {args.output}")
    ser.close()


if __name__ == "__main__":
    main()
