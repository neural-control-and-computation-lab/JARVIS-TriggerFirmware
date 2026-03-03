# JARVIS-TriggerFirmware

## Quick Upload instructions

### Linux

- Clone the repository with:

      git clone --recursive https://github.com/neural-control-and-computation-lab/JARVIS-TriggerFirmware.git

- Setup udev rules by running:

      curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core/develop/platformio/assets/system/99-platformio-udev.rules | sudo tee /etc/udev/rules.d/99-platformio-udev.rules

- Make sure you are in the `JARVIS-TriggerFirmware` Directory and run:

           sh install_arduino_uno.sh

### Windows

- Make sure you have a recent version of Python installed. You can either get it directly from the Microsoft Store or download it from [here](https://www.python.org/downloads/).

- Clone the repository with:

      git clone --recursive https://github.com/neural-control-and-computation-lab/JARVIS-TriggerFirmware.git

- Make sure you are in the `JARVIS-TriggerFirmware` Directory and run:          
      
      .\install_arduino_uno.bat

 - If the install throws an error related to `Long Path Support` first remove the `JARVIS-TriggerFirmware\PlatformIO\install` directory and then open a command prompt as administrator and run:

       reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1


## Analog Input Logging

The firmware automatically streams analog readings from pin A0 at 100 Hz whenever camera trigger pulses are active. A Python proxy script filters the analog data into a CSV file while transparently forwarding all other traffic to the JARVIS acquisition tool. No extra hardware is needed.

### How It Works

    Arduino UNO --USB--> Proxy Script --PTY--> Acquisition Tool
                            |
                            +--> analog_log.csv

The proxy opens the real serial port, creates a virtual serial port (PTY), and forwards all normal JARVIS traffic through to the acquisition tool unchanged. Analog messages are intercepted and logged to CSV instead of being forwarded.

### Recording

1. Install dependencies:

        pip install pyserial cobs

2. Start the proxy **before** the acquisition tool:

        python tool_analog_logger.py --port /dev/ttyACM0 --output analog_log.csv

3. The proxy will print the PTY path. Point the acquisition tool at `/tmp/jarvis_serial` (or the path shown).

4. Start your acquisition as normal. The proxy is transparent to the acquisition tool.

5. Press Ctrl+C to stop the proxy when done. The CSV contains columns: `timestamp_us`, `pulse_id`, `analog_value`.

## Raspberry Pi Pico:
If you encounter a error regarding missing `libhidapi-hidraw0` install it with:

     sudo apt install -y libhidapi-hidraw0


# Contact
JARVIS was developed at the **Neurobiology Lab of the German Primate Center ([DPZ](https://www.dpz.eu/de/startseite.html))**.
If you have any questions or other inquiries related to JARVIS please contact:

Timo Hüser - [@hueser_timo](https://mobile.twitter.com/hueser_timo) - timo.hueser@gmail.com
