import asyncio
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
parser.add_argument("--debug", type=bool, default=False, help="Print stdout of the subprocess")
parser.add_argument("--parse", type=bool, default=False, help="Read input until '###' is parsed.")
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


async def read_until_chars(reader, chars) -> str:
    #output = []
    output = ''
    while True:
        char = await reader.read(1)
        print(f"{char.decode('utf-8')}")
        #if not char:
        #    break
        output += char.decode('utf-8')
        if output[-len(chars):] == chars:
            break
    print('done with msg')
    return "".join(output)
'''

async def read_until_chars(src, chars) -> str:
    output = []
    while True:
        try:
            # Use non-blocking reads with a short timeout
            char = await asyncio.wait_for(src.read(1), timeout=0.1)
        except asyncio.TimeoutError:
            # If a timeout occurs, continue reading
            continue
        except Exception as e:
            # In case of other exceptions, break the loop
            print(f"Error while reading from subprocess: {e}")
            break

        output.append(char.decode())

        if "".join(output[-len(chars):]) == chars:
            break
    return "".join(output)
'''

async def recv_msg(reader) -> str:
    length_binary = await reader.read(4)
    # Extract the 32-bit unsigned integer representing the length
    length = struct.unpack('>I', length_binary)[0]
    # Extract the UTF-8 binary data
    #utf8_binary = sock.recv(length)
    utf8_binary = await reader.read(length)
    return utf8_binary.decode('utf-8')

# Function to handle communication with the client.
async def handle_client(reader, writer):
    # Spawn the subprocess with the provided command.
    '''
    process = subprocess.Popen(
            args.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True, text=True)
    '''
    process = await asyncio.create_subprocess_shell(
        args.command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Function to read from the process and send data to the client.
    async def forward(src, writer):
        while True:
            #data starting= src.readline()
            print('reading chars from subprocess output..')
            data = await read_until_chars(src, '&&&')
            if data:
                if debug:
                    print(data)
                #dst.sendall(encode_string_with_length(data))
                print('bout to write to client')
                writer.write(encode_string_with_length(data))
                await writer.drain()
                #print(f'wrote [{data}] to client')
            else:
                writer.close()
                break

    # Forward stdout and stderr of the subprocess to the client.
    stdout_task = asyncio.create_task(forward(process.stdout, writer))
    stderr_task = asyncio.create_task(forward(process.stderr, writer))

    # Read from the client and send data to the subprocess.
    while True:
        print('await client msg')
        data = await recv_msg(reader)
        print(f'recvd from client: {data}')
        if data:
            #process.stdin.write(data)
            #process.stdin.flush()
            process.stdin.write(data)
            await process.stdin.drain()
        else:
            break

    await stdout_task
    await stderr_task
    #process.stdin.close()
    process.terminate()

def run_client(address, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((address, port))

    try:
        while True:
            user_input = input() + '◊'
            if not user_input:
                break

            client_socket.sendall(encode_string_with_length(user_input))

            response = recv_msg(client_socket)
    finally:
        client_socket.close()

# Sexy global var
debug = args.debug
parse = args.parse

async def main():
    if args.connect:
        run_client(args.connect, args.port)
    else:
        if not args.command:
            print("Error: command is required when running in server mode")
            sys.exit(1)

        # Create a socket server.
        #server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server = await asyncio.start_server(
            handle_client, '127.0.0.1', args.port)

        async with server:
            await server.serve_forever()
        # Bind the server to an address and port.
        #server_address = ('localhost', args.port)
        #server_socket.bind(server_address)

        # Listen for incoming connections.
        #server_socket.listen(1)

if __name__ == '__main__':
    asyncio.run(main())
