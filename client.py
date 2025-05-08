################################################################################################################
# ***IMPORTANT DISCLAIMER***
# Some of the code used in this assignment was borrowed and/or modified from my Homework 2 assignment for CS460. 
# Jeffrey Hoelzel Jr
################################################################################################################

import socket
import threading
import regex as re
import os
import sys

# Constants
SERVER_IP = "127.0.0.1"
PORT = 8080
BUFFER_SIZE = 4096
FILE_PATH_PATTERN = r'^(.+/)*[^/]+\.[a-zA-Z0-9]+$'  # Regex pattern for matching file paths

def clean_file(file_info):
    """Extract sender and file info from received message."""
    sender, file_info = file_info.split(" >> ", 1)
    return sender, file_info

def get_message():
    """Receive messages from the server, including file transfers."""
    while True:
        try:
            message = client.recv(BUFFER_SIZE).decode("utf-8")
            if message == "USERNAME":
                client.send(username.encode("utf-8"))
            elif message == "NEW":
                client.send(f"{username}'s exchange room".encode("utf-8"))
            elif message == "CLOSE":
                client.close()
                print("You have left the exchange room. Ending program.")
                sys.exit(0)
            elif message.startswith("FILE:"):
                file_info = message[5:].replace("\\", "/")  # Normalize path
                sender, file_info = clean_file(file_info)
                if sender != username:
                    get_file(file_info)
            else:
                print(message)
        except Exception as e:
            print(f"[ERROR] get_message: {e}")
            client.close()
            break

def send_message():
    """Send messages or files to the server."""
    while True:
        try:
            message = input()
            if re.match(FILE_PATH_PATTERN, message):  # If input is a file path
                send_file(message.replace("\\", "/"))
            else:
                client.send(f"{username} >> {message}".encode("utf-8"))

            if message == "CLOSE":
                sys.exit(0)
        except Exception as e:
            print(f"[ERROR] send_message: {e}")
            break

def get_file(file_info):
    """Receive a file from the server."""
    try:
        filename, file_size_str = file_info.split(":")
        file_size = int(file_size_str)
        user_dir = os.path.join("received_files", username)
        os.makedirs(user_dir, exist_ok=True)
        full_path = os.path.join(user_dir, os.path.basename(filename))


        print(f"Receiving file '{filename}' ({file_size} bytes)...")

        with open(full_path, "wb") as f:
            bytes_received = 0
            while bytes_received < file_size:
                chunk = client.recv(min(BUFFER_SIZE, file_size - bytes_received))
                if not chunk:
                    break
                f.write(chunk)
                bytes_received += len(chunk)

        print(f"File '{filename}' received successfully. Check your current directory.")
    except Exception as e:
        print(f"[ERROR] get_file: {e}")

def send_file(file_path):
    """Send a file to the server."""
    if not os.path.isfile(file_path):
        print(f"[ERROR] '{file_path}' does not exist.")
        return

    try:
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        client.send(f"FILE:{username} >> {filename}:{file_size}".encode("utf-8"))

        with open(file_path, "rb") as f:
            while True:
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                client.sendall(bytes_read)

        print(f"File '{file_path}' sent successfully.")
    except Exception as e:
        print(f"[ERROR] send_file: {e}")

if __name__ == "__main__":
    username = input("Enter your username: ")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        client.connect((SERVER_IP, PORT))
        print(f"Connected to server\n  IP Address: {SERVER_IP}\n  PORT: {PORT}\n")
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        sys.exit(1)

    # Start threads for receiving and sending
    recv_thread = threading.Thread(target=get_message)
    send_thread = threading.Thread(target=send_message)
    recv_thread.start()
    send_thread.start()
    recv_thread.join()
    send_thread.join()
