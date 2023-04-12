import sys
import socket
import subprocess
import threading
import argparse
from contextlib import closing

# Set up command-line argument parsing.
parser = argparse.ArgumentParser(description="A socket server that runs a command and pipes input/output to the connected client.")
parser.add_argument("command", help="The command to run, including arguments and flags.")
parser.add_argument("--port", type=int, default=12345, help="The port number to bind the server to. (default: 12345)")
args = parser.parse_args()

# Function to handle communication with the client.
def handle_client(client_socket, client_address):
    print(f"Connection received from {client_address}")

    # Spawn the subprocess with the provided command.
    process = subprocess.Popen(args.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)

    # Function to read from the process and send data to the client.
    def forward(src, dst):
        while True:
            data = src.readline()
            if data:
                dst.sendall(data.encode('utf-8'))
            else:
                break

    # Forward stdout and stderr of the subprocess to the client.
    stdout_thread = threading.Thread(target=forward, args=(process.stdout, client_socket))
    stderr_thread = threading.Thread(target=forward, args=(process.stderr, client_socket))

    stdout_thread.start()
    stderr_thread.start()

    # Read from the client and send data to the subprocess.
    while True:
        data = client_socket.recv(1024)
        if data:
            process.stdin.write(data.decode('utf-8'))
            process.stdin.flush()
        else:
            break

    process.terminate()
    stdout_thread.join()
    stderr_thread.join()

    print(f"Connection closed from {client_address}")

# Create a socket server.
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the server to an address and port.
server_address = ('localhost', args.port)
server_socket.bind(server_address)

# Listen for incoming connections.
server_socket.listen(1)
print(f"Server is listening on {server_address}")

# Accept and handle connections.
while True:
    client_socket, client_address = server_socket.accept()
    client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
    client_handler.start()

