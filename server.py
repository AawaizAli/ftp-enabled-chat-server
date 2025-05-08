import socket as s
import sys
import threading as t

# Constants
NUM_CONNECTIONS = 10
HOST_IP = "127.0.0.1"  # localhost
PORT = 8080
BUFFER_SIZE = 2048

# Server running flag
running = True


class FTPRoom:
    def __init__(self, room_name):
        self.name = room_name
        self.clients = []
        self.usernames = []

    def __str__(self):
        return self.name

    def __iter__(self):
        return iter(zip(self.clients, self.usernames))

    def add_client(self, client, username):
        self.clients.append(client)
        self.usernames.append(username)

    def remove_client(self, client, username):
        if client in self.clients:
            self.clients.remove(client)
        if username in self.usernames:
            self.usernames.remove(username)

        try:
            client.send("CLOSE".encode("utf-8"))
        except:
            pass
        finally:
            client.close()

    def send_message(self, message: bytes):
        for client in self.clients:
            try:
                client.send(message)
            except:
                pass


def clean_message(message: str) -> str:
    idx = message.find(">")
    return message[idx + 3:] if idx != -1 else message


def ftp_room_prompt(ftp_rooms, client):
    client.send("USERNAME".encode("utf-8"))
    username = client.recv(BUFFER_SIZE).decode("utf-8")

    welcome = (
        "Welcome to the FTP server!\n"
        "You can either join an existing FTP room or create a new one.\n"
        "Enter the name of the FTP room you wish to join or enter 'NEW' to create a new FTP room.\n"
        "(If none are listed, create one).\n\n"
        "Send any files you want! To quit, enter 'CLOSE'.\n"
    )
    client.send(welcome.encode("utf-8"))

    if ftp_rooms:
        for room in ftp_rooms:
            client.send(f"   {room}\n".encode("utf-8"))
    else:
        client.send("There are no rooms available to join. Create a new one!".encode("utf-8"))

    raw_choice = client.recv(BUFFER_SIZE).decode("utf-8")
    choice = clean_message(raw_choice)

    if "NEW" in choice.upper():
        client.send("NEW".encode("utf-8"))
        room_name = clean_message(client.recv(BUFFER_SIZE).decode("utf-8"))
        return room_name, username

    for room in ftp_rooms:
        if room.name == choice:
            return choice, username

    print(f"{username} failed to specify a valid room. Connection terminated.")
    client.close()
    sys.exit()


def handle_client(ftp_room, client, username):
    while True:
        try:
            message = client.recv(BUFFER_SIZE).decode("utf-8")
            if not message:
                raise ConnectionError("Client disconnected abruptly.")

            if "CLOSE" in message.upper():
                ftp_room.remove_client(client, username)
                print(f"{username} left {ftp_room}.")
                ftp_room.send_message(f"{username} has left the exchange room.".encode("utf-8"))
                break

            ftp_room.send_message(message.encode("utf-8"))

        except Exception as e:
            print(f"Error with {username}: {e}")
            ftp_room.remove_client(client, username)
            break


if __name__ == "__main__":
    print("FTP server booting up...\nTo get started, connect a client.\n")

    server = s.socket(s.AF_INET, s.SOCK_STREAM)
    server.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)

    try:
        server.bind((HOST_IP, PORT))
        server.listen(NUM_CONNECTIONS)
        print(f"{HOST_IP} bound to port {PORT}.")
        print("Listening for connections...")

        exchange_rooms = []
        active_threads = []

        while running:
            server.settimeout(1.0)
            try:
                client, address = server.accept()
                print(f"Connected from {address}.")

                room_name, username = ftp_room_prompt(exchange_rooms, client)

                ftp_room = next((room for room in exchange_rooms if room.name == room_name), None)

                if ftp_room:
                    ftp_room.add_client(client, username)
                    print(f"{username} joined {ftp_room}.")
                    ftp_room.send_message(f"{username} has joined the exchange room!".encode("utf-8"))
                else:
                    ftp_room = FTPRoom(room_name)
                    ftp_room.add_client(client, username)
                    exchange_rooms.append(ftp_room)
                    print(f"{username} created new exchange room '{room_name}'.")
                    ftp_room.send_message(f"{username} has created an exchange room!".encode("utf-8"))

                thread = t.Thread(target=handle_client, args=(ftp_room, client, username))
                thread.start()
                active_threads.append(thread)

            except s.timeout:
                continue
            except Exception as e:
                print(f"Error accepting clients: {e}")

    except KeyboardInterrupt:
        print("\nServer shutdown initiated.")
        running = False
    finally:
        server.close()
        for room in exchange_rooms:
            for client, username in room:
                room.remove_client(client, username)
        for thread in active_threads:
            thread.join(timeout=2)
        print("Server has been shutdown.")
        sys.exit(0)
