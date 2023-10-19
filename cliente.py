import customtkinter
import tkinter
import socket
import sys
import time
import os
import platform
import struct
import subprocess
import vlc

# GLOBALS

root = None # The root window
original_stdout = None
log_stdout = None
entry_ip_port = None # The entry box for "IP:PORT"
dialog = None # The dialog box for errors
client_ip = None
client_port = None
client_socket = None
thread_address = None
video_list = None
is_registered = False
player = None # MPV video player

# CONSTANTS

BEST_UDP_PACKET_SIZE = 1472 # 4 bytes reserved for our counter
COUNTER_SIZE = 4 # 4 bytes reserved for our counter
MESSAGE_SIZE = BEST_UDP_PACKET_SIZE - 4

# LOG FUNCS

def start_log():
    global original_stdout
    global log_stdout

    # Preserve original stdout
    original_stdout = sys.stdout
    # name the log based on port and ip
    sys.stdout = open(f"logs/cliente_" + time.strftime("%Y%m%d-%H%M%S") + ".txt", "w")
    log_stdout = sys.stdout
    print("====================================================================================")
    print("Inicio da execucao: programa que implementa o cliente de streaming de video com udp.")
    print("Gabriel Pimentel Dolzan e Tulio de Padua Dutra - Disciplina Redes de Computadores II")
    print("====================================================================================")
    sys.stdout.flush()  # Flush the file buffer to make sure the data is written
    # return to original stdout
    sys.stdout = original_stdout

def log(message):
    global log_stdout
    global original_stdout
    # Change stdout to log_stdout
    sys.stdout = log_stdout
    print(message)
    sys.stdout.flush()  # Flush the file buffer to make sure the data is written
    # return to original stdout
    sys.stdout = original_stdout

# SOCKET FUNCS

def get_local_ip():
    global client_ip
    # The following trick is used to obtain the IP address. By connecting to a non-local address (doesn't actually make a connection), 
    # the system picks the most appropriate network interface to use. We can then determine the local end of the connection.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect but initiates the system to retrieve a local IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    client_ip = IP

def set_client_port():
    global client_port
    global client_socket
    # Try to bind to a port. If it fails, try the next one.
    for port in range(8522, 8622):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((client_ip, port))
            client_port = port
            client_socket = s
            break
        except OSError:
            continue

def close_client_socket():
    global client_socket
    if client_socket is not None:
        client_socket.close()

def ask_server_for_video_list():
    global thread_address
    global video_list

    video_list = []  # Initialize video_list as an empty list
    # Anexar contador. Vou supor que o contador é um número inteiro e que usaremos struct para formatá-lo como 4 bytes.
    counter = 1  # Suponho que você vai incrementar isso em algum lugar ou mudá-lo conforme necessário.
    counter_bytes = struct.pack('!I', counter)

    log("Enviando mensagem GETLIST para o servidor " + str(thread_address))
    # Criar a mensagem ASKLIST
    message = b"GETLIST".ljust(MESSAGE_SIZE, b'\0')  # Preenchendo a mensagem com zeros para atingir MESSAGE_SIZE

    # Combinar ASKLIST com counter_bytes
    full_message = message + counter_bytes
    
    # Enviar mensagem para o servidor
    client_socket.sendto(full_message, thread_address)
    
    # Esperar resposta do servidor (com timeout)
    while True:
        try:
            client_socket.settimeout(5)  # Definir um timeout de 5 segundos
            data, addr = client_socket.recvfrom(BEST_UDP_PACKET_SIZE)  # Receber até o tamanho BEST_UDP_PACKET_SIZE
        
            # Os 4 últimos bytes são o contador
            received_counter = struct.unpack('!I', data[-COUNTER_SIZE:])[0]
        
            # O restante é a mensagem
            received_message = data[:-COUNTER_SIZE]
            
            if received_message.startswith(b"LIST:"):
                videos_in_message = received_message[5:].decode().split(":")
                video_list.extend(videos_in_message)
            elif received_message == b"ENDLIST":
                return video_list  # Return the accumulated video list
            else:
                print("Resposta inesperada do servidor:", received_message)
                return None

        except socket.timeout:
            print("Timeout ao aguardar resposta do servidor.")
            return None

# TKINTER FUNCS

def on_btn_exit_click():
    global root
    global client_socket
    global is_registered

    if is_registered:
        # Send DEREGISTERUSER to server
        log("Enviando mensagem DEREGISTERUSER para o servidor " + str(thread_address))

        # Preparar a mensagem "DEREGISTERUSER" com o counter
        counter = 1  # Suponho que você incrementará ou mudará conforme necessário.
        counter_bytes = struct.pack('!I', counter)
        message = b"DEREGISTERUSER".ljust(MESSAGE_SIZE, b'\0')  # Preenchendo a mensagem com zeros para atingir MESSAGE_SIZE
        full_message = message + counter_bytes

        # Enviar a mensagem formatada para o servidor
        client_socket.sendto(full_message, thread_address)

        # Esperar DEREGISTERUSEROK
        client_socket.settimeout(5)
        try:
            data, addr = client_socket.recvfrom(BEST_UDP_PACKET_SIZE)

            # Desempacotar counter e verificar a mensagem
            received_counter = struct.unpack('!I', data[-COUNTER_SIZE:])[0]
            received_message = data[:-COUNTER_SIZE]

            if received_message.startswith(b"DEREGISTERUSEROK"):
                log("Servidor respondeu: DEREGISTERUSEROK no endereco " + str(addr))
                is_registered = False
            else:
                log("Servidor respondeu: " + received_message.decode("utf-8"))
        except socket.timeout:
            log("Servidor " + str(thread_address) + " nao respondeu.")

    # Close socket
    log("Fechando socket do cliente.")
    close_client_socket()
    log("Fim da execucao do programa.")
    root.destroy()

def show_error_dialog(parent, message):
    dialog = customtkinter.CTkToplevel(parent)
    dialog.title("Error")
    dialog.geometry("300x150")

    label = customtkinter.CTkLabel(dialog, text=message, font=("Roboto", 18))
    label.pack(pady=30)

    def on_btn_ok_click():
        dialog.destroy()

    ok_button = customtkinter.CTkButton(dialog, text="OK", font=("Roboto", 18), command=on_btn_ok_click)
    ok_button.pack(pady=10)

    dialog.transient(parent)  # Set the dialog to be a transient window of the parent.
    dialog.grab_set()  # Make the dialog modal.
    parent.wait_window(dialog)  # Wait until the dialog is destroyed.

def is_valid_ip(ip_address):
    try:
        socket.inet_aton(ip_address)
        return True
    except socket.error:
        return False

def is_valid_port(port):
    try:
        port_number = int(port)
        if 0 < port_number <= 65535:
            return True
        return False
    except ValueError:
        return False

def on_btn_connect_click():
    global entry_ip_port
    global root
    global client_socket
    global thread_address
    global is_registered
    
    ip_port_value = entry_ip_port.get()  # Get the value from the entry
    if ":" not in ip_port_value:
        show_error_dialog(root, "Invalid IP or PORT")
        return

    ip, port = ip_port_value.split(":")
    if not is_valid_ip(ip) or not is_valid_port(port):
        show_error_dialog(root, "Invalid IP or PORT")
        return

    log("Tentando contato com o servidor IP:" + ip + " - Porta:" + port)

    log("Enviando mensagem REGISTERUSER para o servidor " + str(thread_address))

    # Preparar a mensagem "REGISTERUSER" com o counter
    counter = 1  # Suponho que você incrementará ou mudará conforme necessário.
    counter_bytes = struct.pack('!I', counter)
    message = b"REGISTERUSER".ljust(MESSAGE_SIZE, b'\0')  # Preenchendo a mensagem com zeros para atingir MESSAGE_SIZE
    full_message = message + counter_bytes

    # Enviar a mensagem formatada para o servidor
    client_socket.sendto(full_message, (ip, int(port)))

    # Esperar resposta
    client_socket.settimeout(5)
    try:
        data, addr = client_socket.recvfrom(BEST_UDP_PACKET_SIZE)

        # Desempacotar counter e verificar a mensagem
        received_counter = struct.unpack('!I', data[-COUNTER_SIZE:])[0]
        received_message = data[:-COUNTER_SIZE]

        if received_message.startswith(b"REGISTERUSEROK"):
            log("Servidor respondeu: REGISTERUSEROK no endereco " + str(addr))
            is_registered = True
            thread_address = addr
            show_client_list()
        else:
            log("Servidor respondeu: " + received_message.decode("utf-8"))
            show_error_dialog(root, "Erro ao se conectar com o servidor.\n Tente novamente.")
    except socket.timeout:
        log("Servidor IP:" + ip + " - Porta:" + port + " nao respondeu.")
        show_error_dialog(root, "Erro ao se conectar com o servidor.\n Tente novamente.")


def create_connect_menu():
    global entry_ip_port  
    global root  
    # set appearance to dark
    customtkinter.set_appearance_mode("dark")
    # set color theme to blue
    customtkinter.set_default_color_theme("green")

    root = customtkinter.CTk()
    root.title("Cliente")
    root.geometry("500x350")

    # Create a frame
    frame = customtkinter.CTkFrame(root)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Create a label
    label = customtkinter.CTkLabel(frame, text="Cliente", font=("Roboto", 36))
    label.pack(pady=24, padx=10)

    # Create an entry box for "IP:PORT"
    entry_ip_port = customtkinter.CTkEntry(frame, font=("Roboto", 18), placeholder_text="IP:PORT", justify="center", width=200)
    entry_ip_port.pack(pady=10, padx=10)

    # Create a button "Conectar"
    button_connect = customtkinter.CTkButton(frame, text="Conectar", font=("Roboto", 18), width=200, command=on_btn_connect_click)
    button_connect.pack(pady=10, padx=10, side="left", expand=True)

    # Create a button "Sair"
    button_exit = customtkinter.CTkButton(frame, text="Sair", font=("Roboto", 18), width=200, fg_color="red", hover_color="darkred", command=on_btn_exit_click)
    button_exit.pack(pady=10, padx=10, side="left", expand=True)

    return root

def show_client_list():
    global root

    # Clear the root window
    for widget in root.winfo_children():
        widget.destroy()

    # Adjusting the geometry for a vertical strip
    root.geometry("360x600")
    video_list = ask_server_for_video_list()
    log("Lista de videos recebida do servidor: " + str(video_list))

    # Here, you can start populating the root window with new content.
    frame = customtkinter.CTkFrame(root)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    # A label for representation
    label = customtkinter.CTkLabel(frame, text="Lista de Videos", font=("Roboto", 36))
    label.pack(pady=24, padx=10)

    # A Scrollable Frame for the list of videos, with each video being a button
    scrollable_frame = customtkinter.CTkScrollableFrame(frame)
    scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # A button for each video
    for video in video_list:
        button = customtkinter.CTkButton(scrollable_frame, text=video, font=("Roboto", 18), command=lambda video_name=video: play_video(video_name))
        button.pack(pady=10, padx=10, fill="x")

    # Exit button placed at the bottom
    btn_exit = customtkinter.CTkButton(root, text="Sair", font=("Roboto", 18), fg_color="red", hover_color="darkred", command=on_btn_exit_click)
    btn_exit.pack(pady=10, padx=10, fill="x")

def stop_playing_video():
    global player

    if player:
        player.stop()  # Terminate the MPV player instance
        player = None
    show_client_list()

def play_video(video_name):
    global root
    global player

    # Clear the root window
    for widget in root.winfo_children():
        widget.destroy()

    # Change geometry for 1280x720
    root.geometry("1280x720")

    # Main frame
    main_frame = customtkinter.CTkFrame(root)
    main_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Video frame
    video_frame = customtkinter.CTkFrame(main_frame)
    video_frame.pack(fill="both", expand=True, pady=(0, 10))

    # Set up VLC player in the video frame
    vlc_instance = vlc.Instance("--no-xlib", "--quiet")
    player = vlc_instance.media_player_new()

    # Embed VLC player into the tkinter frame
    player.set_xwindow(video_frame.winfo_id())

    # Load and play the video
    video_path = os.path.join("videos", video_name)
    player.set_mrl(video_path)
    player.play()
    player.audio_set_volume(50)

    # Controls frame
    controls_frame = customtkinter.CTkFrame(main_frame)
    controls_frame.pack(fill="x", pady=(0, 10), padx=10)

    # Pause/Play button
    def toggle_play_pause():
        if player.is_playing():
            player.pause()
            btn_pause_play.configure(text="Play")
        else:
            player.play()
            btn_pause_play.configure(text="Pause")
            update_duration()

    btn_pause_play = customtkinter.CTkButton(controls_frame, text="Pause", font=("Roboto", 14), command=toggle_play_pause)
    btn_pause_play.pack(side='left', padx=5)

    # Forward and Backward buttons
    btn_backward = customtkinter.CTkButton(controls_frame, text="<< 10s", font=("Roboto", 14), command=lambda: update_duration())
    btn_backward.pack(side='left', padx=5)

    btn_forward = customtkinter.CTkButton(controls_frame, text=">> 10s", font=("Roboto", 14), command=lambda: update_duration())
    btn_forward.pack(side='left', padx=5)

    def update_duration():
        print("this would update the video seek bar and the texts.")

    # Current duration label
    lbl_duration = customtkinter.CTkLabel(controls_frame, text="0:00", font=("Roboto", 14))
    lbl_duration.pack(side='left', padx=5)

    # Use more space for the seek bar
    seek_slider = customtkinter.CTkSlider(controls_frame, width=400)
    seek_slider.pack(side='left', padx=5, fill="x", expand=True)

    # Total duration label
    lbl_total_time = customtkinter.CTkLabel(controls_frame, text="0:00", font=("Roboto", 14))
    lbl_total_time.pack(side='left', padx=5)

    lbl_current_volume = customtkinter.CTkLabel(controls_frame, text=str(int(player.volume)), font=("Roboto", 14))
    lbl_current_volume.pack(side='left', padx=5)

    def adjust_volume(lbl_current_volume, event=None):
        volume = max(0, min(100, int(volume_slider.get())))
        player.audio_set_volume(volume)
        lbl_current_volume.configure(text=str(volume))

    # Compact volume slider
    volume_slider = customtkinter.CTkSlider(controls_frame, width=100, from_=0, to=100)
    volume_slider.set(50)
    volume_slider.bind("<ButtonRelease-1>", lambda event, lbl=lbl_current_volume: adjust_volume(lbl, event))
    volume_slider.pack(side='left', padx=5)

    # Stop button
    btn_stop = customtkinter.CTkButton(controls_frame, text="Stop", font=("Roboto", 14), fg_color="red", hover_color="darkred", command=stop_playing_video)
    btn_stop.pack(side='right', padx=5)

# GENERAL CLIENT FUNCS

def init_client():
    global root
    # Get ip and port from "Cliente"
    get_local_ip()
    set_client_port()
    # Start log
    start_log()
    log("Socket UDP do Cliente criado com sucesso - IP: " + client_ip + " - Porta: " + str(client_port))
    # Start Graphical Interface
    root = create_connect_menu()
    root.mainloop()


if __name__ == "__main__":
    init_client()