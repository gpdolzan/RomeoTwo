import sys
import socket
import time
import os
from queue import PriorityQueue

BUFFER_SIZE = 1452  # Adjust this based on your network's performance.

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

def listener(output_file, port):
    global packet_counter
    local_ip = get_local_ip()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((local_ip, port))
    print(f"Listening on {local_ip}:{port}...")
    s.settimeout(20)  # Set timeout to 20 seconds

    try:
        with open(output_file, 'wb') as f:
            while True:
                try:
                    data, addr = s.recvfrom(BUFFER_SIZE)
                    # Assuming the data packet structure is (counter, actual_data)
                    counter, actual_data = data[0:4], data[4:]
                    packet_queue.put((counter, actual_data))
                    # Increment and print the counter
                    print(f"Received packet: {packet_counter}")
                    packet_counter += 1
                except socket.timeout:
                    print("No packets received for 20 seconds. Exiting...")
                    break

            while not packet_queue.empty():
                _, packet_data = packet_queue.get()
                f.write(packet_data)
                
    finally:
        s.close()

def main():
    if len(sys.argv) < 3:
        print("Usage: python client-side.py output_file client_port")
        sys.exit(1)

    output_name = sys.argv[1]
    client_port = int(sys.argv[2])
    listener(output_name, client_port)

if __name__ == "__main__":
    main()
