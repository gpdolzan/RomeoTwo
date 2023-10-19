import socket
import time
import threading
import vlc
import subprocess
import re

# Configuração do servidor
VIDEO = "videos/yellow.ts"
SERVER_IP = '192.168.68.127'
SERVER_PORT = 12345
BUFFER_SIZE = 65507  # MTU IPV4 - 20 (IP header) - 8 (UDP header)

clients = set()  # Lista de clientes registrados


def get_video_bitrate(video_path):
    # Executando o ffprobe para pegar informações do arquivo de vídeo
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=bit_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Verificando se a saída contém o bitrate
    bitrate_match = re.search(r'(\d+)', result.stdout)
    if bitrate_match:
        print(f"Bitrate do vídeo: {bitrate_match.group(1)} bps")
        return int(bitrate_match.group(1))
    
    raise Exception("Não foi possível obter o bitrate do vídeo")

def get_video_duration(video_path):
    # Executando o ffprobe para pegar a duração do arquivo de vídeo
    command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Verificando se a saída contém a duração
    duration_match = re.search(r'(\d+\.\d+)', result.stdout)
    if duration_match:
        print(f"Duração do vídeo: {duration_match.group(1)} segundos")
        return float(duration_match.group(1))
    
    raise Exception("Não foi possível obter a duração do vídeo")

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

BITRATE = get_video_bitrate(VIDEO)
BYTES_PER_SECOND = BITRATE / 8

# print bytes per second
print(f"Bytes por segundo: {BYTES_PER_SECOND}")

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
