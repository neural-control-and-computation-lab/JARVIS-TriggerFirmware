#ifndef _TRIGGERPINS_ARDUINO_UNO
#define _TRIGGERPINS_ARDUINO_UNO

// Outputs (digital pins 0-13)
#define OUT00_PIN 0
#define OUT01_PIN 1
#define OUT02_PIN 2
#define OUT03_PIN 3
#define OUT04_PIN 4
#define OUT05_PIN 5
#define OUT06_PIN 6
#define OUT07_PIN 7
#define OUT08_PIN 8
#define OUT09_PIN 9
#define OUT10_PIN 10
#define OUT11_PIN 11
#define OUT12_PIN 12
#define OUT13_PIN 13
#define OUT14_PIN -1 // A0 reserved for analog input
#define OUT15_PIN -1 // A1 not used as trigger on UNO

// Inputs (A2-A5 on UNO, pins 20-23 do not exist)
#define IN00_PIN 16
#define IN01_PIN 17
#define IN02_PIN 18
#define IN03_PIN 19
#define IN04_PIN -1
#define IN05_PIN -1
#define IN06_PIN -1
#define IN07_PIN -1

// Analog input pin for continuous logging
#define ANALOG_PIN A0

#endif
