import socket
import customtkinter
import threading
import sys
import time
import os
import subprocess
import struct

# GLOBALS
original_stdout = None
log_stdout = None
server_running = False
server_ip = None
server_socket = None
registered_users = []
video_list = []
log_lock = threading.Lock()
registered_users_lock = threading.Lock()

# CONSTANTES
SERVER_PORT = 8521
BEST_UDP_PACKET_SIZE = 1472
COUNTER_SIZE = 4 # 4 bytes reserved for our counter
MESSAGE_SIZE = BEST_UDP_PACKET_SIZE - 4

# SOCKET FUNCS

def get_local_ip():
    global server_ip
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
    server_ip = IP

def set_thread_socket():
    global server_ip
    # Try to bind to a port. If it fails, try the next one.
    for port in range(8420, 8520):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind((server_ip, port))
            return s
            break
        except OSError:
            continue
    # If we get here, we couldn't bind to any port, open dialog and exit
    show_error_dialog(root, "Nao foi possivel abrir uma porta para o servidor.")
    log("Nao foi possivel abrir uma porta para a thread do usuario.")
    return None


# Dedicated thread to handle communication with a particular user
def user_thread(addr, thread_socket):
    global video_list
    while server_running:
        data, user_addr = thread_socket.recvfrom(BEST_UDP_PACKET_SIZE)
        if user_addr != addr:
            continue  # Not the right user for this thread

        # Desempacotar counter e verificar a mensagem
        received_counter = struct.unpack('!I', data[-COUNTER_SIZE:])[0]
        received_message = data[:-COUNTER_SIZE]

        # Tratar mensagens diferentes aqui
        if received_message.startswith(b"GETLIST"):
            log("Cliente solicitou lista de videos, enviando para " + str(addr))

            # Convert the video list to a string
            video_string = ":".join(video_list)

            # Calculate how many bytes we can send in each message
            max_data_size = BEST_UDP_PACKET_SIZE - COUNTER_SIZE - 5 # 5 = "LIST:"

            # Split the video list into chunks that fit within the data size limit
            chunks = [video_string[i:i + max_data_size] for i in range(0, len(video_string), max_data_size)]

            for chunk in chunks:
                # Construct the message with the "LIST:" prefix
                message = b"LIST:" + chunk.encode()

                # Attach the counter
                counter_bytes = struct.pack('!I', received_counter)
                full_message = message + counter_bytes

                # Send the chunk
                thread_socket.sendto(full_message, addr)

                # Increment the counter for the next message
                received_counter += 1

            # Send the ENDLIST message
            end_message = b"ENDLIST" + struct.pack('!I', received_counter)
            thread_socket.sendto(end_message, addr)
        elif received_message.startswith(b"DEREGISTERUSER"):
            with registered_users_lock:
                registered_users.remove(addr)
            log(f"Cliente {addr} solicitou para ser removido da lista de usuarios registrados.")

            # Send DEREGISTERUSEROK
            counter_bytes = struct.pack('!I', received_counter + 1)
            response_message = b"DEREGISTERUSEROK".ljust(MESSAGE_SIZE, b'\0')  # Preenchendo a mensagem para atingir MESSAGE_SIZE
            full_response = response_message + counter_bytes

            log(f"Enviando DEREGISTERUSEROK para {addr}")
            thread_socket.sendto(full_response, addr)

            # end thread loop
            break

    # Close socket
    log(f"Fechando socket da thread {addr}.")
    thread_socket.close()

# LOG FUNCS

def start_log():
    global original_stdout
    global log_stdout

    # Preserve original stdout
    original_stdout = sys.stdout
    # name the log based on port and ip
    sys.stdout = open(f"logs/server_" + time.strftime("%Y%m%d-%H%M%S") + ".txt", "w")
    log_stdout = sys.stdout
    print("=====================================================================================")
    print("Inicio da execucao: programa que implementa o servidor de streaming de video com udp.")
    print("Gabriel Pimentel Dolzan e Tulio de Padua Dutra - Disciplina Redes de Computadores II")
    print("=====================================================================================")
    sys.stdout.flush()  # Flush the file buffer to make sure the data is written
    # return to original stdout
    sys.stdout = original_stdout


def log(message):
    global log_stdout
    global original_stdout
    global log_lock
    
    with log_lock:
        # Change stdout to log_stdout
        sys.stdout = log_stdout
        print(message)
        sys.stdout.flush()  # Flush the file buffer to make sure the data is written
        # return to original stdout
        sys.stdout = original_stdout

# VIDEO LIST FUNCS

def read_video_list():
    with open("list/video_list.txt", "r") as file:
        video_list = file.read().splitlines()
    return video_list
                

def view_videos_folder():
    # get name of all .ts videos in the folder videos
    videos = [f for f in os.listdir("videos") if os.path.isfile(os.path.join("videos", f)) and f.endswith(".ts")]
    return videos

def update_video_list():
    global video_list
    folder = view_videos_folder()
    video_list = read_video_list()

    # check if there are new videos
    for video in folder:
        if video not in video_list:
            log(f"Novo video encontrado: {video}, adicionando a lista")

            # write new video to video_list.txt
            with open("list/video_list.txt", "a") as file:
                file.write(video + "\n")
            # add new video to video_list
            video_list.append(video)

    log("Lista de videos atualizada com sucesso")
    return

# TKINTER FUNCS

def on_btn_exit_click():
    global root
    global server_running
    global server_socket
    server_running = False

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

def create_server_gui():
    global root
    # set appearance to dark
    customtkinter.set_appearance_mode("dark")
    # set color theme to blue
    customtkinter.set_default_color_theme("green")

    root = customtkinter.CTk()
    root.title("Servidor")
    root.geometry("400x250")

    # Create a frame
    frame = customtkinter.CTkFrame(root)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    # Create a label
    label = customtkinter.CTkLabel(frame, text="Servidor em execução", font=("Roboto", 36))
    label.pack(pady=24, padx=10)

    # Create a button "Sair"
    button_exit = customtkinter.CTkButton(frame, text="Sair", font=("Roboto", 18), fg_color="red", hover_color="darkred", command=on_btn_exit_click)
    button_exit.pack(pady=10, padx=10, side="left", expand=True)

    return root

def run_server():
    global server_running
    global server_ip
    global root
    global server_socket
    server_running = True
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        # Try to bind to port 8521, if it fails, abort, there is another server running
        try:
            server_socket.bind((server_ip, SERVER_PORT))
            log("Socket UDP do Servidor criado com sucesso - IP: " + server_ip + " - Porta: " + str(SERVER_PORT))
        except OSError:
            log("Ja existe um servidor em execucao nessa maquina.")
            show_error_dialog(root, "Ja existe um servidor aberto.")
            log("Fim da execucao do programa.")

            server_running = False
            root.destroy()  # This will close the main window and end the program
            return

        while server_running:  # using the flag to control the loop
            data, addr = server_socket.recvfrom(BEST_UDP_PACKET_SIZE)
            with registered_users_lock:
                if addr in registered_users:
                    continue  # Ignore registered users in the main loop

            # Desempacotar counter e verificar a mensagem
            received_counter = struct.unpack('!I', data[-COUNTER_SIZE:])[0]
            received_message = data[:-COUNTER_SIZE]

            if received_message.startswith(b"REGISTERUSER"):
                thread_socket = set_thread_socket()
                if thread_socket is not None:
                    counter_bytes = struct.pack('!I', received_counter + 1)  # Incrementar o contador para a resposta
                    response_message = b"REGISTERUSEROK".ljust(MESSAGE_SIZE, b'\0')  # Preenchendo a mensagem para atingir MESSAGE_SIZE
                    full_response = response_message + counter_bytes

                    thread_socket.sendto(full_response, addr)
                    registered_users.append(addr)
                    log(f"Cliente registrado: {addr}, iniciando thread com endereco {thread_socket.getsockname()}")
                    threading.Thread(target=user_thread, args=(addr, thread_socket), daemon=True).start()

        # close socket
        log("Fechando socket principal do servidor.")
        server_socket.close()

# MAIN
if __name__ == "__main__":
    # Get ip "Servidor"
    get_local_ip()
    start_log()
    update_video_list()
    root = create_server_gui()
    threading.Thread(target=run_server, daemon=True).start()
    root.mainloop()
