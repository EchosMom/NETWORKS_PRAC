"""Sends and recieves"""

import socket
import threading
import protocol
import ProtocolUtils

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500
peerPort = 1600

"""Makes connection with server or the peer."""
def connect_client():
    connection= input("Connect to server or peer? s/p: ")
    
    if connection == "s":
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            clientSocket.connect((serverAddress, serverPort))
            print("Connection successful.")
        except:
            print("Error: Connection failed.")

        # Creates threads to recieve replies from the server
        threading.Thread(target=receive_reply, args=(clientSocket,), daemon=True).start()
        send_request(clientSocket)

    elif connection == "p":
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.bind(("0.0.0.0", peerPort))
        listenSocket.listen()

        # Creates threads to listen for messages from peers
        threading.Thread(target=receive_message, args=(listenSocket,), daemon=True).start()
        send_message()

"""Sends requests to the server."""
def send_request(clientSocket):
    while True:
        request = input("Enter request or 'exit' to quit: ")
        if request =="exit":
            clientSocket.close()
            break
        try:
            rq = ProtocolUtils(
                headers={
                    "messageType": protocol.MessageType.COMMAND,
                    "message": request,
                    "sender": "client",
                    "recipient": serverAddress})
            clientSocket.send(rq.encode())
        except:
              print("Error: request not sent.")
              break

"""Receives replies from the server and prints them to the console."""
def receive_reply(clientSocket):
    while True:
        try:
            reply = clientSocket.recv(protocol.MAX_MESSAGE_BODY_SIZE)
            if not reply:
                print("Connection ended.")
                break
            else:
                rp = ProtocolUtils.decode(reply)
                print(rp.body.decode())
        except:
            print("Error: reply not received.")
            break

"""Sends messages to peer."""
def send_message():
    while True:  # Loops to send messages to different peers
        peerIP = input("Enter peer IP or 'exit' to quit: ")
        if peerIP == "exit":
            break
        try:
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect((peerIP, peerPort))
            print("Connection successful.")
            while True:  # Loops to send messages to the same peer
                try:
                    message = input("Enter message or 'exit' to change peers: ")
                    if message == "exit":
                        peerSocket.close()
                        break
                    else:
                        msg = ProtocolUtils(
                        headers={
                            "messageType": protocol.MessageType.CHAT,
                            "message": protocol.Messages.TEXT,
                            "sender": "peer",
                            "recipient": peerIP},
                             body= message.encode())
                        peerSocket.send(msg.encode())        
                except:
                    print("Error: message not sent.")
                    peerSocket.close()
                    break
        except:
            print("Connection unsuccessful.")

"""Receives messages from peer and prints them to the console."""
def receive_message(listenSocket):
    while True:  # Loops to accept connection and message from different peers
        try:
            new_socket, new_address = listenSocket.accept()
            message = new_socket.recv(protocol.MAX_MESSAGE_BODY_SIZE)
            if not message:
                print("Connection ended.")
            else:
                msg = ProtocolUtils.decode(message)
                print(msg.body.decode())
                new_socket.close()
        except:
            print("Error: message not received.")
            break

if __name__ == '__main__':
    connect_client()