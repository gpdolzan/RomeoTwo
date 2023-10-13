import socket
import subprocess
import re
import time

def get_local_ip():
    """Fetches the local LAN IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # This line doesn't actually try to connect, but the OS initializes the networking system to determine the most appropriate network interface
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip

HOST = get_local_ip()
PORT = 0

clients = []

def get_video_duration(filename):
    command = ['ffmpeg', '-i', filename]
    result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    # Regex para encontrar a duração no output do ffmpeg
    match = re.search(r"Duration: (\d+:\d+:\d+\.\d+)", result.stderr)
    if match:
        h, m, s = map(float, match.group(1).split(':'))
        return h * 3600 + m * 60 + s
    return None

def start_stream(filename, fps, server_socket, clients):
    ffmpeg_command = [
        'ffmpeg',
        '-i', filename,
        '-f', 'mpegts',
        '-codec:v', 'h264',
        '-s', '640x360',
        '-an',  # Ignore audio for simplicity
        '-vf', f"fps={fps}",
        '-']

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    video_duration = get_video_duration(filename)
    frame_count = 0
    packet_id = 1

    try:
        for frame in iter(lambda: process.stdout.read(4096), b''):
            for client in clients:
                server_socket.sendto(f"{packet_id}\n".encode() + frame, client)
            
            # Atualize o frame_count
            frame_count += 1
            current_time = frame_count / fps
            remaining_time = video_duration - current_time

            if frame_count % fps == 0:
                print(f"Atual: {current_time:.2f} segundos, Restante: {remaining_time:.2f} segundos")

            packet_id += 1
    except KeyboardInterrupt:
        pass

    process.terminate()
    process.wait()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    print(f"Server started on {HOST}:{PORT}")

    while True:
        data, addr = server_socket.recvfrom(1024)
        if data.decode() == "REGISTER":
            clients.append(addr)
            print(f"Registered client: {addr}")

        elif data.decode() == "UNREGISTER" and addr in clients:
            clients.remove(addr)
            print(f"Unregistered client: {addr}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: serverStream.py <filename> <fps> <port>")
        sys.exit(1)

    filename = sys.argv[1]
    fps = float(sys.argv[2])
    PORT = int(sys.argv[3])

    try:
        main()
    finally:
        start_stream(filename, fps)
