"""
------ TILTING STATION CONTROL ------

While the ESP32 runs the .ino and additional files, this .py file is run by the user in order to wirelessly send
the message with the movement characteristics.

--- Note: ---
Before use, align the top gear so that the station is upright.

To control, send the controller a message indicating:
"{movement},{position},{speed}"

--- Modes: ---
TURN OFF MOTORS  - message = "Off,0,0"
TILT             - message = f"Tilt,{position},{speed}"
                        For position send a value between [0, 180).
ROTATECCW        - message = f"RotateCCW,{position},{speed}"
ROTATECW         - message = f"RotateCW,{position},{speed}"
                        For position (both cases) send a value between [0, 360).
FULLROTATION     - message = f"FullRotation,{position},{speed}"
                        -1 for position means 1 rotation CCW.
                         1 for position means 1 rotation CW.
GOHOME           - message = "Home,0,0"

--- Example: ---

message = "Tilt,90,0"
Type: Tilt,90,0
0 is default speed.

message = "RotateCW,120,0"
Type: RotateCW,120,0
0 is default speed.

message = "FullRotation,2,0"
Type: FullRotation,2,0
0 is default speed.

Speed is measured in microseconds. It is the amount of delay between each signal pulse. 
Use numbers greater than 1000. Bigger numbers mean slower movement.

"""

# Import libraries
import socket
import os

# ESP32 variables
# ** Make sure laptop is connected to robot network
esp32_ip = "192.168.12.101"
esp32_port = 80

# Open socket communication with ESP32
print("Sending message to ESP32...")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # .AF_INET - For IPv4 addresses; .SOCK_STREAM - Socket type is TCP
    s.connect((esp32_ip, esp32_port))
    # Send a string in the format stated above.
    # message = f"{movement},{position},{speed}"
    message = input("Message: ")
    s.sendall(message.encode("utf-8")) 
    print("Message sent: ", message)
    s.close()