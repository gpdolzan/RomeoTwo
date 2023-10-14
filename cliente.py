import socket
import subprocess

# Configuração do cliente
SERVER_IP = '192.168.68.127'
SERVER_PORT = 12345

BUFFER_SIZE = 65507
client_port = 12346  # Pode ser alterado para cada cliente

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', client_port))

    # Registrar com o servidor
    s.sendto(b'REGISTER', (SERVER_IP, SERVER_PORT))

    # Reprodução de vídeo com VLC
    player = subprocess.Popen(["vlc", "fd://0"], stdin=subprocess.PIPE)

    last_counter = 0
    buffer = {}  # Buffer para pacotes fora de ordem

    while True:
        data, addr = s.recvfrom(BUFFER_SIZE)
        counter = int.from_bytes(data[:4], 'big')

        if counter == last_counter + 1:
            player.stdin.write(data[4:])
            last_counter += 1

            # Verifique se há pacotes subsequentes no buffer
            while last_counter + 1 in buffer:
                player.stdin.write(buffer[last_counter + 1])
                del buffer[last_counter + 1]
                last_counter += 1
        else:
            # Armazene o pacote no buffer se ele chegar fora de ordem
            buffer[counter] = data[4:]

if __name__ == '__main__':
    main()
