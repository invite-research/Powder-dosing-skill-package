/* 
------ TILTING STATION CONTROL ------

The pulley ratio is 1:3, meaning the 400 steps and 0.9° resolution are actually 1200 steps and 0.3° on the bigger pulley.

To control, send the controller a message indicating:
"{movement},{position},{mov_speed}".

Examples:
* "Tilt,90,0"
* "RotateCW,120,0"
* "FullRotation,1,0"
* "GripperOpen,2.0,0"
* "GripperClose,1.5,0"

For the gripper:
- reference state is fully closed = 0.0 cm
- maximum opening = 5.5 cm
- "GripperOpen,2.0,0"  -> opens 2.0 cm more
- "GripperClose,1.5,0" -> closes 1.5 cm more
- command is clamped between 0.0 cm and 5.5 cm

Speed refers to the wait time between each pulse of the stepper, in microseconds.
Use values greater than 1000. Bigger values mean slower movement.
For the gripper, speed 0 uses the default speed from code.

--- Note: ---
Before use, align the top gear so that the station is upright.

--------------------------------------------------------------------
*/

// Import pins, libraries and variables.
#include "pins_and_variables.h"
// Include additional functions
#include "other_functions.h"
#include "Discovery.h"

void setup() {
  Serial.begin(115200);

  pinMode(enPin_L, OUTPUT);
  pinMode(dirPin_L, OUTPUT);
  pinMode(stepPin_L, OUTPUT);

  pinMode(enPin_R, OUTPUT);
  pinMode(dirPin_R, OUTPUT);
  pinMode(stepPin_R, OUTPUT);

  pinMode(enPin_G, OUTPUT);
  pinMode(dirPin_G, OUTPUT);
  pinMode(stepPin_G, OUTPUT);

  digitalWrite(stepPin_L, LOW);
  digitalWrite(stepPin_R, LOW);
  digitalWrite(stepPin_G, LOW);

  digitalWrite(dirPin_L, LOW);
  digitalWrite(dirPin_R, LOW);
  digitalWrite(dirPin_G, LOW);

  delay(10000);

  // Disable motors at startup
  digitalWrite(enPin_L, LOW);
  digitalWrite(enPin_R, LOW);
  digitalWrite(enPin_G, HIGH);   // TMC2209 disable

  /*
  // Start Access Point
  Serial.println("Setting Access Point...");
  WiFi.softAP(ssid, password);
  Serial.print("The IP is: ");
  Serial.println(WiFi.softAPIP());
  server.begin();
  Serial.println("Access Point set.");
  */
  WiFi.setHostname("POTS");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("Connected to WiFi");
  Serial.print("Hostname: ");
  Serial.println(WiFi.getHostname());

  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("RSSI: ");
  Serial.println(WiFi.RSSI());

  server.begin();
  startDiscovery();
  Serial.println("TCP server started. Waiting for connections.");

  delay(3000);

  // Offset to 94° to fix accuracy issue
  Serial.println("Offsetting...");
  new_position_tilt = 90 + 4;
  tilt_station();
  current_position_tilt = 90;

  // Prepare station for placing container
  new_position_tilt = 70;
  tilt_station();
  new_position_tilt = 90;
  tilt_station();

  // Initial gripper reference state
  gripper_current_opening_cm = 0.0;
  gripper_requested_delta_cm = 0.0;
  gripper_current_steps = 0;
  gripper_target_steps = 0;
  gripper_action = "";

  Serial.println("Gripper reference state set to CLOSED (0.0 cm).");

  digitalWrite(enPin_L, LOW);
  digitalWrite(enPin_R, LOW);
  digitalWrite(enPin_G, HIGH);
  Serial.println("Motors deactivated.");

  Serial.println("System ready to use.");
  /*delay(50);*/
  yield();
}

void loop() {
  handleDiscovery();
  if (!client || !client.connected()) {
    client = server.available();
    if (client) {
      Serial.println("Connection established.");
      Serial.print("Client connected: ");
      Serial.println(client.remoteIP());  
    }
  }

  if (client && client.connected()) {
    while (client.available()) {
      message = client.readStringUntil('\n');
      message.trim();
      Serial.print("Received data: ");
      Serial.println(message);
    }

    if (message.length() > 0) {
      interpret_message();
      message = "";
    }
  }

  if (new_position_rotation != current_position_rotation) {
    if (direction_rotation == "CW") {
      rotate_CW(mov_speed);
    }
    else if (direction_rotation == "CCW") {
      rotate_CCW(mov_speed);
    }

    Serial.print("Rotation position: ");
    Serial.println(current_position_rotation);
    new_position_rotation = current_position_rotation;
  }
  else if (new_position_tilt != current_position_tilt) {
    tilt_station(mov_speed);

    Serial.print("Tilt position: ");
    Serial.println(current_position_tilt);

    new_position_tilt = current_position_tilt;
  }
  else if (gripper_action == "OPEN") {
    open_gripper_by_cm(gripper_requested_delta_cm, mov_speed);
    gripper_requested_delta_cm = 0.0;
    gripper_action = "";
  }
  else if (gripper_action == "CLOSE") {
    close_gripper_by_cm(gripper_requested_delta_cm, mov_speed);
    gripper_requested_delta_cm = 0.0;
    gripper_action = "";
  }

  delay(50);
}
