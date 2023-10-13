import socket
import subprocess
import os

# leia HOST e PORT do input
HOST = input("Host: ")
PORT = int(input("Port: "))

def main():
    # Configurações
    server_address = ("localhost", 12345)
    lost_packets = 0
    out_of_order_packets = 0
    last_packet_id = 0

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(10)  # Timeout de 10 segundos
    client_socket.sendto(b"REGISTER", server_address)

    # Para fins de depuração: escreva o stream em um arquivo
    with open("debug_output.ts", "wb") as outfile:
        try:
            while True:
                data, _ = client_socket.recvfrom(65536)
                packet_id, content = data.split(b'\n', 1)
                packet_id = int(packet_id)

                if packet_id <= last_packet_id:
                    out_of_order_packets += 1

                lost_packets += packet_id - last_packet_id - 1
                last_packet_id = packet_id

                # Escreva os dados recebidos no arquivo para depuração
                outfile.write(content)

        except KeyboardInterrupt:
            print(f"\n--- Estatísticas ---")
            print(f"Pacotes perdidos: {lost_packets}")
            print(f"Pacotes fora de ordem: {out_of_order_packets}")

if __name__ == "__main__":
    main()
