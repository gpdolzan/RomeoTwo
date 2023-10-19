import socket
import vlc
import time
import tkinter as tk

# Configuração do cliente
SERVER_IP = '192.168.68.127'
SERVER_PORT = 12345

BUFFER_SIZE = 65507
client_port = 12346  # Pode ser alterado para cada cliente

def play_video_from_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', client_port))

    # Registrar com o servidor
    s.sendto(b'REGISTER', (SERVER_IP, SERVER_PORT))

    # Setting up VLC player
    instance = vlc.Instance("--no-xlib")
    player = instance.media_player_new()
    media = instance.media_new('fd://0')  # File descriptor '0' stands for stdin
    player.set_media(media)

    last_counter = 0
    buffer = {}  # Buffer for out-of-order packets

    player.play()
    time.sleep(0.5)  # Give VLC a bit of time to initialize

    while True:
        data, addr = s.recvfrom(BUFFER_SIZE)
        counter = int.from_bytes(data[:4], 'big')

        if counter == last_counter + 1:
            player.get_media().get_mrl().write(data[4:])
            last_counter += 1

            # Check for subsequent packets in the buffer
            while last_counter + 1 in buffer:
                player.get_media().get_mrl().write(buffer[last_counter + 1])
                del buffer[last_counter + 1]
                last_counter += 1
        else:
            # Store the packet in the buffer if it arrives out of order
            buffer[counter] = data[4:]

if __name__ == '__main__':
    # Create a basic tkinter window to manage VLC's rendering
    root = tk.Tk()
    root.title("Video Player")
    root.geometry("640x480")
    play_video_from_socket()
    root.mainloop()
