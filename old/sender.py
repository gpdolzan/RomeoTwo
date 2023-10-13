import socket

def udp_sender(target_ip, target_port, message):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send message
    server_address = (target_ip, target_port)
    sock.sendto(message.encode('utf-8'), server_address)

if __name__ == "__main__":
    target_ip = input("Enter the target IP address: ")
    target_port = int(input("Enter the target port number: "))
    message = input("Enter your message: ")
    udp_sender(target_ip, target_port, message)
    print(f"Message sent to {target_ip}:{target_port}")