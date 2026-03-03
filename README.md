# JARVIS-TriggerFirmware

## Installation

### Linux

1. Clone the repository:

        git clone --recursive https://github.com/neural-control-and-computation-lab/JARVIS-TriggerFirmware.git

2. Setup PlatformIO udev rules:

        curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core/develop/platformio/assets/system/99-platformio-udev.rules | sudo tee /etc/udev/rules.d/99-platformio-udev.rules

3. From the `JARVIS-TriggerFirmware` directory, run:

        sh install_arduino_uno.sh

4. Unplug and replug the Arduino so the udev rule takes effect.

### Windows

1. Make sure you have a recent version of Python installed ([download](https://www.python.org/downloads/)).

2. Clone the repository:

        git clone --recursive https://github.com/neural-control-and-computation-lab/JARVIS-TriggerFirmware.git

3. From the `JARVIS-TriggerFirmware` directory, run:

        .\install_arduino_uno.bat

   If the install throws an error related to `Long Path Support`, first remove the `JARVIS-TriggerFirmware\PlatformIO\install` directory, then open a command prompt as administrator and run:

        reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1

## Analog Input Logging

The firmware streams analog readings from pin A0 at 100 Hz whenever trigger pulses are active. A proxy script (`tool_analog_logger.py`) sits between the Arduino and the acquisition tool, logging analog data to CSV while forwarding all other traffic transparently. No extra hardware or changes to the acquisition tool are needed.

### Recording

1. Start the proxy before the acquisition tool:

        python tool_analog_logger.py --output analog_log.csv

2. Start the acquisition tool as normal.

3. Press Ctrl+C to stop the proxy when done.

The CSV contains columns: `timestamp_us`, `pulse_id`, `analog_value`. Without the proxy running, the acquisition tool works exactly as before.

## Raspberry Pi Pico

If you encounter an error regarding missing `libhidapi-hidraw0`, install it with:

    sudo apt install -y libhidapi-hidraw0

## Contact

JARVIS was developed at the **Neurobiology Lab of the German Primate Center ([DPZ](https://www.dpz.eu/de/startseite.html))**.
If you have any questions or other inquiries related to JARVIS please contact:

Timo Hüser - [@hueser_timo](https://mobile.twitter.com/hueser_timo) - timo.hueser@gmail.com
