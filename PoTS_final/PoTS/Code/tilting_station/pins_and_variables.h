// Libraries
#include <WiFi.h>
#include <WiFiServer.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>

// Constants
/*
// ** Access Point
const char* ssid = "Tilting_Station_AP";       // For remote control with Access Point
const char* password = "123456789";            // ESP32 static IP is 192.168.1.100
*/
// ** uLab credentials
const char* ssid = "uLM15-206000855";
const char* password = "dXNlcjp1cmcsIHBhc3M6Y29iaW90aXg=";
const uint16_t DISCOVERY_PORT = 4210;

// ** Motor control
// Pulley ratio is 1:3
const int stepsPerRevolution = 400 * 3;        // 400 pulses per revolution.
const float degreePerStep = 0.9 / 3;           // Consider pulley ratio.
const float offsetRotation = 0;
const float offsetTilt = 0;

// ** Gripper motor control
// Observation-based calibration:
// current test gave about 45° motion, but full required motion is 90°.
// Therefore set full open/close travel to 400 step pulses for now.
// Tune this later if actual 5.5 cm travel does not match perfectly.
const int defaultGripperSpeed = 1200;          // microseconds between step transitions
const int gripperFullTravelSteps = 400;        // full motion from 0.0 cm to 5.5 cm
const float gripperMaxOpeningCm = 5.5;
const float gripperStepsPerCm = (float)gripperFullTravelSteps / gripperMaxOpeningCm;

// If direction is reversed physically, swap these two levels.
const int gripperOpenDirLevel = HIGH;
const int gripperCloseDirLevel = LOW;

// Variables
// ** Socket communication
String message;
String direction_rotation;
String gripper_action = "";

// ** Motor control
int current_position_tilt = 90;
int current_position_rotation = 0;
int new_position_tilt = 90;
int new_position_rotation = 0;
int mov_speed = 0;

// ** Gripper state
float gripper_current_opening_cm = 0.0;        // reference state: fully closed = 0.0 cm
float gripper_requested_delta_cm = 0.0;
int gripper_current_steps = 0;                 // reference state: fully closed = 0 steps
int gripper_target_steps = 0;

// Objects
// ** Access Point
WiFiClient client;
WiFiServer server(80);                         // Set on port 80
WiFiUDP udp;

// Pins
// ** Left motor
#define enPin_L 12
#define dirPin_L 10
#define stepPin_L 8

// ** Right motor
#define enPin_R 6
#define dirPin_R 4
#define stepPin_R 2

// ** Gripper motor (TMC2209)
#define enPin_G 7
#define dirPin_G 5
#define stepPin_G 3