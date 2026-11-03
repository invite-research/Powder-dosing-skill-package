import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(3)

sock.sendto(b"DISCOVER_POTS", ("192.168.12.255", 4210))

try:
    data, addr = sock.recvfrom(1024)
    print("Reply:", addr)
    print(data.decode())
except socket.timeout:
    print("No reply")