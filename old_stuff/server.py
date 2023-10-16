import socket
import time
import threading
import subprocess
import re
from moviepy.editor import VideoFileClip

# Configuração do servidor
VIDEO = "yellow_1080_ts.ts"
SERVER_IP = '192.168.68.127'
SERVER_PORT = 12345
BUFFER_SIZE = 65507  # MTU IPV4 - 20 (IP header) - 8 (UDP header)

clients = set()  # Lista de clientes registrados

def get_video_bitrate(filename):
    cmd = ["ffmpeg", "-i", filename]
    result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = result.communicate()

    # Search for bitrate in the FFmpeg output
    matches = re.search(r"bitrate: (\d+) kb/s", stdout.decode('utf-8'))
    if matches:
        return int(matches.group(1)) * 1000  # Convert kbps to bps

    return None  # Return None if bitrate couldn't be extracted

def get_video_duration(filename):
    clip = VideoFileClip(filename)
    duration = clip.duration
    clip.close()
    return duration

def read_video(filename):
    with open(filename, 'rb') as file:
        while True:
            data = file.read(BUFFER_SIZE - 4)  # 4 bytes reserved for the counter
            if not data:
                break
            yield data

def listen_for_clients(s):
    while True:
        data, addr = s.recvfrom(BUFFER_SIZE)
        if data == b'REGISTER':
            clients.add(addr)
            print(f"Cliente registrado: {addr}")

BITRATE = get_video_bitrate(VIDEO) or 5000000
BYTES_PER_SECOND = BITRATE / 8
VIDEO_DURATION = get_video_duration(VIDEO)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SERVER_IP, SERVER_PORT))

    print(f"Servidor iniciado em {SERVER_IP}:{SERVER_PORT}")

    # Começar a escutar os registros em uma thread separada
    threading.Thread(target=listen_for_clients, args=(s,), daemon=True).start()

    input("Pressione ENTER para começar a transmitir o vídeo...")

    # Imprimir que estamos começando a transmitir
    print("Iniciando transmissão de vídeo...")

    counter = 0
    # Ler vídeo e enviar em chunks
    for data in read_video(VIDEO):
        counter += 1
        msg = counter.to_bytes(4, 'big') + data  # Prefix the data with the counter
        for client in clients:
            s.sendto(msg, client)

        # Adjust sleep based on the amount of data sent and the video's bitrate
        sleep_duration = len(data) / BYTES_PER_SECOND
        time.sleep(sleep_duration)

    print("Transmissão de vídeo concluída")

if __name__ == '__main__':
    main()
