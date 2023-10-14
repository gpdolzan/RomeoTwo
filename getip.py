import socket

def get_local_ip():
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
    return IP

print(get_local_ip())