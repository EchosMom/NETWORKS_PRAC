"""Sends and recieves"""

import socket
import threading

serverAddres = "127.0.0.1"  # Localhost
serverPort = 1500

"""Makes connection with server."""
def connect_client():
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        clientSocket.connect((serverAddres, serverPort))
        print("Connection successful.")
    except:
        print("Error: Connection failed.")

    threading.Thread(target=receive_reply, args=(clientSocket,)).start()
    send_request(clientSocket)

"""Sends requests to the server."""
def send_request(clientSocket):
    while True:
        request= input()
        if request=="exit":
            clientSocket.close()
            break
        try:
            clientSocket.send(request.encode())
        except:
              print("Error: request not sent.")
              break

"""Receives replies from the server and prints them to the console."""
def receive_reply(clientSocket):
    while True:
        try:
            reply= clientSocket.recv(1024)
            if not reply:
                print("Connection ended.")
                break
            else:
                print(reply.decode())
        except:
            print("Error: reply not received.")
            break


if __name__ == '__main__':
    connect_client()