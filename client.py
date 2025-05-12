import tkinter as tk
from tkinter import simpledialog, filedialog, scrolledtext
import threading
import socket
import os
import re

SERVER_IP = "127.0.0.1"
PORT = 8080
BUFFER_SIZE = 2048
FILE_PATH_PATTERN = r'^(.+/)*[^/]+\.[a-zA-Z0-9]+$'

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Global variables (set after login)
username = ""
exchange_room = ""
user_dir = ""
app = None

class LoginWindow:
    def __init__(self, master):
        self.master = master
        master.title("Login to Exchange Room")
        master.geometry("300x150")

        self.label1 = tk.Label(master, text="Enter Username:")
        self.label1.pack(pady=5)
        self.username_entry = tk.Entry(master)
        self.username_entry.pack()

        self.label2 = tk.Label(master, text="Enter Exchange Room Name:")
        self.label2.pack(pady=5)
        self.room_entry = tk.Entry(master)
        self.room_entry.pack()

        self.connect_button = tk.Button(master, text="Join", command=self.connect)
        self.connect_button.pack(pady=10)

    def connect(self):
        global username, exchange_room, user_dir
        username = self.username_entry.get().strip()
        exchange_room = self.room_entry.get().strip()
        if username and exchange_room:
            try:
                client.connect((SERVER_IP, PORT))
            except OSError as e:
                print("Connection error:", e)
                return
            self.master.destroy()
            user_dir = os.path.join(os.getcwd(), username, exchange_room)
            os.makedirs(user_dir, exist_ok=True)
            show_chat_ui()

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{username} in {exchange_room}")
        self.root.geometry("600x400")

        self.chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=70)
        self.chat_area.pack(padx=10, pady=5)
        self.chat_area.config(state='disabled')

        self.entry_field = tk.Entry(root, width=50)
        self.entry_field.pack(side=tk.LEFT, padx=10, pady=5)

        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT)

        self.file_button = tk.Button(root, text="Send File", command=self.send_file_dialog)
        self.file_button.pack(side=tk.LEFT)

    def update_chat(self, msg):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, msg + "\n")
        self.chat_area.yview(tk.END)
        self.chat_area.config(state='disabled')

    def send_message(self):
        msg = self.entry_field.get()
        if msg:
            try:
                client.send(f"{username} >> {msg}".encode("utf-8"))
            except OSError:
                self.update_chat("Error: Disconnected from server.")
            self.entry_field.delete(0, tk.END)

    def send_file_dialog(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            send_file(file_path)

def get_file(file_info):
    filename, file_size_str = file_info.split(":")
    file_size = int(file_size_str)
    full_path = os.path.join(user_dir, os.path.basename(filename))
    with open(full_path, "wb") as f:
        bytes_received = 0
        while bytes_received < file_size:
            chunk = client.recv(min(BUFFER_SIZE, file_size - bytes_received))
            if not chunk:
                break
            f.write(chunk)
            bytes_received += len(chunk)
    app.update_chat(f"File '{filename}' received successfully. Saved in {user_dir}")

def send_file(file_path):
    if not os.path.isfile(file_path):
        app.update_chat(f"File not found: {file_path}")
        return
    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    try:
        client.send(f"FILE:{username} >> {filename}:{file_size}".encode("utf-8"))
        with open(file_path, "rb") as f:
            while chunk := f.read(BUFFER_SIZE):
                client.sendall(chunk)
        app.update_chat(f"Sent file: {filename}")
    except OSError:
        app.update_chat("Error: Failed to send file. Disconnected from server.")

def receive():
    while True:
        try:
            msg = client.recv(BUFFER_SIZE).decode("utf-8")
            if msg == "USERNAME":
                client.send(username.encode("utf-8"))
            elif msg == "NEW":
                client.send(f"{exchange_room}".encode("utf-8"))
            elif msg == "CLOSE":
                client.close()
                break
            elif msg.startswith("FILE:"):
                sender, file_info = msg[5:].split(" >> ", 1)
                if sender != username:
                    get_file(file_info)
            else:
                app.update_chat(msg)
        except:
            break

def show_chat_ui():
    global app
    chat_root = tk.Tk()
    app = ChatApp(chat_root)
    threading.Thread(target=receive, daemon=True).start()
    chat_root.mainloop()

# Launch login first
if __name__ == "__main__":
    login_root = tk.Tk()
    LoginWindow(login_root)
    login_root.mainloop()
