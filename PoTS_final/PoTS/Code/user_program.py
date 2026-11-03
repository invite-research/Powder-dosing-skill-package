"""
------ TILTING STATION CONTROL ------
Program for the user.

While the ESP32 runs the .ino and additional files, this .py file is run by the user in order to wirelessly send
the message with the movement characteristics.

To control, send the controller a message indicating:
"{movement},{position},{speed}"

--- Note: ---
Before use, align the top gear so that the station is upright.

"""

# Import libraries
import socket
import os

# Access Point variables
ssid = "Tilting_Station_AP";   
password = "123456789";             # Not used in code.
esp32_ip = "192.168.4.1"
esp32_port = 80

# Connect to the ESP32 Access Point
# ** Only after first connection has been established and AP is known.
# ** If connection fails, comment this part and connect manually.
print("Connecting to Access Point...")
os.system('cmd /c "netsh wlan show networks"')                          # Scan available networks.
os.system(f'''cmd /c "netsh wlan connect name={ssid}"''')               # Connect to Access Point.

while True:
    # Ask the user for the command.
    print("----- TILTING STATION CONTROL -----")
    while True:
        input_1 = int(input("Press:\n 1 to tilt,\n 2 to rotate CCW,\n 3 to rotate CW,\n 4 to do a full rotation,\n 5 to rotate for time,\n 6 to home,\n 0 to end program,\n-1 to deactivate motors. \n"))
        match input_1:
            case 0:
                movement = False
                break
            case 1:
                movement = "Tilt"
                position = int(input("Type a number between 0 and 180 for the position. \n"))
                set_speed = input("Set speed? Y/N ")
                speed = int(input("Speed: ")) if set_speed == "Y" or set_speed == "y" else 0
                break
            case 2:
                movement = "RotateCCW"
                position = int(input("Type a number between 0 and 360 for the position. \n"))
                set_speed = input("Set speed? Y/N ")
                speed = int(input("Speed: ")) if set_speed == "Y" or set_speed == "y" else 0
                break
            case 3:
                movement = "RotateCW"
                position = int(input("Type a number between 0 and 360 for the position. \n"))
                set_speed = input("Set speed? Y/N ")
                speed = int(input("Speed: ")) if set_speed == "Y" or set_speed == "y" else 0
                break
            case 4:
                movement = "FullRotation"
                position = int(input("Type the number of revolutions. Negative numbers mean CCW. \n"))
                set_speed = input("Set speed? Y/N ")
                speed = int(input("Speed: ")) if set_speed == "Y" or set_speed == "y" else 0
                break
            # Currently in development
            # case 5:
            #     movement = "RotateTime"
            #     position = int(input("Type the desired time for rotation (seconds). Negative numbers mean CCW. \n"))
            #     set_speed = input("Set speed? Y/N ")
            #     speed = int(input("Speed: ")) if set_speed == "Y" or set_speed == "y" else 0
            #     break
            case 6:
                movement = "Home"
                position = 0
                speed = 0
                break
            case -1:
                movement = "Off"
                position = 0
                speed = 0
                break
            case _:
                movement = False
                print("Input not valid.")
        
    if movement:
        # Open socket communication with ESP32
        print("Sending message to ESP32...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # .AF_INET - For IPv4 addresses; .SOCK_STREAM - Socket type is TCP
            s.connect((esp32_ip, esp32_port))
            message = f"{movement},{position},{speed}"
            s.sendall(message.encode("utf-8")) 
            print("Message sent: ", message)
            s.close()
    else: 
        break