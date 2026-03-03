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

The firmware automatically streams analog readings from pin A0 at 100 Hz whenever camera trigger pulses are active. To record this data, run the included Python logger alongside your acquisition:

    pip install pyserial cobs
    python tool_analog_logger.py --port /dev/ttyACM0 --output analog_log.csv

The logger passively listens on the serial port and writes a CSV with columns: `timestamp_us`, `pulse_id`, `analog_value`. Press Ctrl+C to stop. No changes to your existing acquisition workflow are needed — just run the logger in a separate terminal.

## Raspberry Pi Pico:
If you encounter a error regarding missing `libhidapi-hidraw0` install it with:

     sudo apt install -y libhidapi-hidraw0


# Contact
JARVIS was developed at the **Neurobiology Lab of the German Primate Center ([DPZ](https://www.dpz.eu/de/startseite.html))**.
If you have any questions or other inquiries related to JARVIS please contact:

Timo Hüser - [@hueser_timo](https://mobile.twitter.com/hueser_timo) - timo.hueser@gmail.com
