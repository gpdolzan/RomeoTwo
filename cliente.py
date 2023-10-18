import customtkinter
import tkinter
import socket
import sys
import time
import vlc
import os
import platform
import struct

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
                is_registered = True
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
    root.geometry("360x720")
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
        button = customtkinter.CTkButton(scrollable_frame, text=video, font=("Roboto", 18), command=show_main_client_interface)
        button.pack(pady=10, padx=10, fill="x")

    # Exit button placed at the bottom
    btn_exit = customtkinter.CTkButton(root, text="Sair", font=("Roboto", 18), fg_color="red", hover_color="darkred", command=on_btn_exit_click)
    btn_exit.pack(pady=10, padx=10, fill="x")

def show_main_client_interface():
    global root
    global vlc_instance  # Make sure the vlc_instance is global or managed properly

    # Clear the root window
    for widget in root.winfo_children():
        widget.destroy()

    # Change geometry for 720p
    root.geometry("1280x720")

    # Here, you can start populating the root window with new content.aa
    frame = customtkinter.CTkFrame(root)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    # A label for representation
    #label = customtkinter.CTkLabel(frame, text="Main Client Interface", font=("Roboto", 36))
    #label.pack(pady=24, padx=10)

    # Create a Frame for VLC player inside the main frame
    vlc_frame = tkinter.Frame(frame)
    vlc_frame.pack(pady=20, fill=tkinter.BOTH, expand=True)

    # VLC setup
    vlc_instance = vlc.Instance()
    player = vlc_instance.media_player_new()
    
    if platform.system() == "Windows":
        player.set_hwnd(vlc_frame.winfo_id())
    elif platform.system() == "Darwin":  # macOS
        from ctypes import c_void_p
        ns_view = c_void_p(vlc_frame.winfo_id())
        player.set_nsobject(ns_view.value)
    elif platform.system() == "Linux":
        player.set_xwindow(vlc_frame.winfo_id())
    else:
        raise Exception("Unsupported OS")

    # Add a play button or other controls if necessary
    btn_play = customtkinter.CTkButton(frame, text="Play Video", command=lambda: play_video(player))
    btn_play.pack(pady=20)

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

# TESTE

def play_video(player):
    # This plays the video inside the frame.
    # You can use any video source, such as a file path or a streaming URL.
    media = vlc_instance.media_new('videos/yellow.ts')
    player.set_media(media)
    player.play()


if __name__ == "__main__":
    init_client()