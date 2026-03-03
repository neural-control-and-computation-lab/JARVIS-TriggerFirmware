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

The firmware automatically streams analog readings from pin A0 at 100 Hz whenever camera trigger pulses are active. A transparent proxy intercepts the analog data into a CSV file while forwarding all other traffic to the acquisition tool unchanged. No extra hardware or changes to the acquisition tool are needed.

### How It Works

The install script sets up a udev rule that creates `/dev/ttyJARVIS` as an alias for the Arduino. When the proxy runs, it temporarily redirects `/dev/ttyACM0` to a virtual serial port so the acquisition tool connects through the proxy without any configuration changes.

    Arduino (/dev/ttyJARVIS) --> Proxy --> /dev/ttyACM0 (PTY) --> Acquisition Tool
                                  |
                                  +--> analog_log.csv

### Setup

Everything is installed automatically by the install script:

    sh install_arduino_uno.sh

After installing, **unplug and replug the Arduino** so the udev rule takes effect.

### Recording

1. Start the proxy **before** the acquisition tool:

        python tool_analog_logger.py --output analog_log.csv

2. Start the acquisition tool as normal. It connects to `/dev/ttyACM0` automatically — the proxy is fully transparent.

3. Press Ctrl+C to stop the proxy when done. The CSV contains columns: `timestamp_us`, `pulse_id`, `analog_value`.

Without the proxy running, the acquisition tool works exactly as before — no proxy needed for normal (non-analog) use.

## Raspberry Pi Pico:
If you encounter a error regarding missing `libhidapi-hidraw0` install it with:

     sudo apt install -y libhidapi-hidraw0


# Contact
JARVIS was developed at the **Neurobiology Lab of the German Primate Center ([DPZ](https://www.dpz.eu/de/startseite.html))**.
If you have any questions or other inquiries related to JARVIS please contact:

Timo Hüser - [@hueser_timo](https://mobile.twitter.com/hueser_timo) - timo.hueser@gmail.com
