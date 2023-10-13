import sys
import socket
import os
import time
from moviepy.editor import VideoFileClip

MAX_UDP_PAYLOAD_IPV4 = 1452

def get_video_info(file_name):
    with VideoFileClip(file_name) as clip:
        fps = clip.fps
        duration = clip.duration
        n_frames = clip.reader.nframes
        size = clip.size

    info = {
        "fps": fps,
        "duration": duration,
        "n_frames": n_frames,
        "width": size[0],
        "height": size[1]
    }

    return info

def calculate_send_interval(video_file, info):
    # Estimate average bytes per frame
    total_bytes_of_video = os.path.getsize(video_file)
    average_bytes_per_frame = total_bytes_of_video / info['n_frames']

    # Estimate packets required per frame
    packets_per_frame = average_bytes_per_frame / MAX_UDP_PAYLOAD_IPV4

    # Calculate send interval
    send_interval = (1/info['fps']) / packets_per_frame
    return send_interval

def process_video(video_file, server_ip, server_port, send_interval, client_addresses):
    info = get_video_info(video_file)
    print(f"Video Information: {info}")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    counter = 0
    with open(video_file, 'rb') as f:
        chunk = f.read(MAX_UDP_PAYLOAD_IPV4 - 4)  # 4 bytes for the counter
        while chunk:
            # Prepend the 4-byte counter to the data chunk
            data_to_send = counter.to_bytes(4, 'big') + chunk
            
            for client_addr in client_addresses:
                s.sendto(data_to_send, client_addr)
            
            # Update the counter
            counter = (counter + 1) % (2**32)  # Ensure it wraps around when reaching max uint32 value
            
            time.sleep(send_interval)  # Sleep based on the provided or calculated interval
            
            chunk = f.read(MAX_UDP_PAYLOAD_IPV4 - 4)

def main():
    if len(sys.argv) < 3:
        print("Usage: python server-side.py video_file server_port [send_interval]")
        sys.exit(1)

    video_file = sys.argv[1]
    server_port = int(sys.argv[2])

    # Assuming you want to use the local IP address for the server
    server_ip = socket.gethostbyname(socket.gethostname())
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((server_ip, server_port))
    
    print(f"Starting server on {server_ip}:{server_port}")

    client_addresses = set()
    print("Waiting for clients to register...")
    
    # Let's say we wait for 60 seconds for clients to register before starting to send the video
    start_time = time.time()
    while time.time() - start_time < 60:
        try:
            s.settimeout(1)  # check each second
            data, client_address = s.recvfrom(1024)
            if data.decode('utf-8') == 'REGISTER':
                client_addresses.add(client_address)
                print(f"Registered client: {client_address}")
        except socket.timeout:
            pass
    
    print(f"Registered clients: {client_addresses}")

    info = get_video_info(video_file)
    calculated_interval = calculate_send_interval(video_file, info)

    # show the user the calculated interval
    print(f"Calculated send interval: {calculated_interval}")

    # Check for user-specified interval
    if len(sys.argv) == 4:
        user_interval = float(sys.argv[3])
        if user_interval > calculated_interval:
            print("Warning: The specified interval may result in buffering or slow video playback rate.")
        send_interval = user_interval
    else:
        send_interval = calculated_interval

    process_video(video_file, server_ip, server_port, send_interval, client_addresses)

if __name__ == "__main__":
    main()