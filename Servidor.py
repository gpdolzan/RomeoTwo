import socket
import customtkinter
import threading
import sys
import time

# GLOBALS
original_stdout = None
log_stdout = None
server_running = False
server_ip = None
registered_users = []
log_lock = threading.Lock()

# CONSTANTES
SERVER_PORT = 8521
BEST_UDP_PACKET_SIZE = 1472 - 4 # 4 bytes reserved for our counter

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

# Dedicated thread to handle communication with a particular user
def user_thread(addr, server_socket):
    while server_running:
        data, user_addr = server_socket.recvfrom(BEST_UDP_PACKET_SIZE)
        if user_addr != addr:
            continue  # Not the right user for this thread

        # Handle other messages from the user here.
        # For example, just echoing back for now:
        server_socket.sendto(data, addr)

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

# TKINTER FUNCS

def on_btn_exit_click():
    global root
    global server_running
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
            if data == b"REGISTERUSER":
                log(f"MENSAGEM: REGISTERUSER de {addr}, respondendo com REGISTERUSEROK")
                server_socket.sendto(b"REGISTERUSEROK", addr)
                registered_users.append(addr)
                log(f"Cliente registrado: {addr}, iniciando thread.")
                threading.Thread(target=user_thread, args=(addr, server_socket), daemon=True).start()

# MAIN
if __name__ == "__main__":
    # Get ip "Servidor"
    get_local_ip()
    start_log()
    root = create_server_gui()
    threading.Thread(target=run_server, daemon=True).start()
    root.mainloop()
