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

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Allow the socket to reuse the address
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        local_ip = get_local_ip()
        print(f"Attempting to bind to {local_ip}:{client_port}...")
    
        s.bind((local_ip, client_port))
    
        # Register with the server
        s.sendto("REGISTER".encode(), (server_ip, client_port))

        
        s.settimeout(20)  # Set timeout outside the loop

        print(f"Listening for packets from {server_ip}:{client_port}...")

        last_received_time = time.time()
        with open(output_name, 'wb') as f:
            while True:
                try:
                    data, _ = s.recvfrom(MAX_UDP_PAYLOAD_IPV4)
                    counter = int.from_bytes(data[:4], 'big')
                    f.write(data[4:])
                    print(f"Received packet: {counter}")
                    last_received_time = time.time()
                except socket.timeout:
                    # If 20 seconds have passed since the last packet, we assume it's done.
                    print("No packets received for 20 seconds. Exiting.")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
