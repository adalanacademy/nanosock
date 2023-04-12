import sys
import socket
import struct
import subprocess
import threading
import argparse
from contextlib import closing

# Set up command-line argument parsing.
parser = argparse.ArgumentParser(description="A socket server/client that runs a command and pipes input/output to the connected client.")
parser.add_argument("command", nargs='?', help="The command to run, including arguments and flags.")
parser.add_argument("--port", type=int, default=12345, help="The port number to bind the server to or connect to. (default: 12345)")
parser.add_argument("--connect", "-c", type=str, help="The address to connect as a client.")
args = parser.parse_args()

def encode_string_with_length(s: str) -> bytes:
    # Convert the string to UTF-8 binary
    utf8_binary = s.encode('utf-8')

    # Get the length of the encoded string
    length = len(utf8_binary)

    # Prepend a 32-bit unsigned integer representing the length
    length_binary = struct.pack('>I', length)

    # Return the combined binary data
    return length_binary + utf8_binary

def recv_msg(sock) -> str:
    length_binary = sock.recv(4)
    # Extract the 32-bit unsigned integer representing the length
    length = struct.unpack('>I', length_binary)[0]
    # Extract the UTF-8 binary data
    utf8_binary = sock.recv(length)
    return utf8_binary.decode('utf-8')

# Function to handle communication with the client.
def handle_client(client_socket, client_address):
    # Spawn the subprocess with the provided command.
    process = subprocess.Popen(args.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)

    # Function to read from the process and send data to the client.
    def forward(src, dst):
        while True:
            #data = src.readline()
            data = src.readline()
            if data:
                #dst.sendall(data.encode('utf-8'))
                dst.sendall(encode_string_with_length(data))
            else:
                break

    # Forward stdout and stderr of the subprocess to the client.
    stdout_thread = threading.Thread(target=forward, args=(process.stdout, client_socket))
    stderr_thread = threading.Thread(target=forward, args=(process.stderr, client_socket))

    stdout_thread.start()
    stderr_thread.start()

    # Read from the client and send data to the subprocess.
    while True:
        #data = client_socket.recv(1024)
        data = recv_msg(client_socket)
        if data:
            process.stdin.write(data)
            process.stdin.flush()
        else:
            break

    process.terminate()
    stdout_thread.join()
    stderr_thread.join()

def run_client(address, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((address, port))

    try:
        while True:
            user_input = input() + '\n'
            if not user_input:
                break

            client_socket.sendall(encode_string_with_length(user_input))

            response = recv_msg(client_socket)
    finally:
        client_socket.close()

if args.connect:
    run_client(args.connect, args.port)
else:
    if not args.command:
        print("Error: command is required when running in server mode")
        sys.exit(1)

    # Create a socket server.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the server to an address and port.
    server_address = ('localhost', args.port)
    server_socket.bind(server_address)

    # Listen for incoming connections.
    server_socket.listen(1)

    # Accept and handle connections.
    while True:
        client_socket, client_address = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

