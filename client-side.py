import sys
import socket
import time
import os
from queue import PriorityQueue

BUFFER_SIZE = 1452  # Adjust this based on your network's performance.
MAX_UDP_PAYLOAD_IPV4 = 1452

packet_counter = 0
packet_queue = PriorityQueue()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't matter if the IP below is unreachable, we use it to determine the most appropriate source IP.
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    if len(sys.argv) < 4:
        print("Usage: python client-side.py output_file server_ip client_port")
        sys.exit(1)

    output_name = sys.argv[1]
    server_ip = sys.argv[2]
    client_port = int(sys.argv[3])

    # Register with the server
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto("REGISTER".encode(), (server_ip, client_port))
    
    print(f"Listening for packets from {server_ip}:{client_port}...")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((get_local_ip(), client_port))

    with open(output_name, 'wb') as f:
        last_received_time = time.time()
        while True:
            s.settimeout(20)  # If no packets are received in 20 seconds, it will raise a timeout exception.
            try:
                data, _ = s.recvfrom(MAX_UDP_PAYLOAD_IPV4)
                counter = int.from_bytes(data[:4], 'big')
                f.write(data[4:])
                print(f"Received packet: {counter}")
                last_received_time = time.time()
            except socket.timeout:
                # If 20 seconds have passed since the last packet, we assume it's done.
                if time.time() - last_received_time >= 20:
                    print("No packets received for 20 seconds. Exiting.")
                    break

if __name__ == "__main__":
    main()
