"""Sends and recieves"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import socket
import threading
import protocol
import ProtocolUtils

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500
peerPort = 1600
mediaPort = 1700 #this is for sending media files, UDP_port
chunkSize = 65536 #bytes per UDP packet


#UDP sockets
#mediaSendSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#mediareceiveSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#mediareceiveSocket.bind(("0.0.0.0", mediaPort))

#cleint must login to serever
def loginToServer():
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        clientSocket.connect((serverAddress, serverPort))
        print("Connection successful.")
    except Exception as e:
        print("Error: Connection failed.")
        return None

   
    usernameInput = input("Enter username: ")
    passwordInput = input("Enter password: ")

    login_msg = ProtocolUtils.ProtocolUtils(
        headers={
            "MessageType": protocol.MessageType.COMMAND,
            "Message": protocol.Messages.LOGIN,
            "Sender": usernameInput,
            "Recipient": serverAddress,
            "Username": usernameInput,
            "Password": passwordInput
        },
        body=b""
    )
    clientSocket.send(login_msg.encode())


    
    # Wait for server reply, if login fails, close socket and return None
    while True:
        replyBytes = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
        if not replyBytes:
            print("Server disconnected.")
            clientSocket.close()
            return None
        reply = ProtocolUtils.ProtocolUtils.decode(replyBytes)
        if reply.message == protocol.Messages.ACK:
            print(f"Login successful: {reply.body.decode()}")
            #thread to listen for sever message
            threading.Thread(target=receive_reply, args=(clientSocket,), daemon=True).start()
            return (usernameInput, clientSocket)
        elif reply.message == protocol.Messages.ERROR:
            print(f"Login failed: {reply.body.decode()}")
            return None

"""Sends requests to the server."""
def send_request(clientSocket, username, recipient):
    request = input("Enter server request: ")
    if request =="P2P_REQ":
        try:
            rq = ProtocolUtils.ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.P2P_REQ,
                    "Sender": username,
                    "Recipient": recipient},
                body=b"")
            clientSocket.send(rq.encode())
        except Exception as e:
            print("Error: request not sent.", e)
    # Still need to add code for other requests

"""Receives replies from the server and prints them to the console."""
def receive_reply(clientSocket):
    while True:
        try:
            reply = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
            if not reply:
                print("Server disconnected.")
                break
            rp = ProtocolUtils.ProtocolUtils.decode(reply)
            type= rp.headers.get("MessageType")
            if type == protocol.MessageType.COMMAND:
                print(f"[Server]: {rp.body.decode()}")
            elif type == protocol.MessageType.P2P_REQ:
                print("You received P2P chat request")
                ip= listenSocket.getsockname()[0]
                #port= listenSocket.getsockname()[1]
                offer = ProtocolUtils.ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.P2P_OFFER,
                    "Sender": rp.headers.get("Recipient"),
                    "Recipient": rp.headers.get("Sender")},
                body= ip.encode())
                #f"{ip}:{port}".encode())
                clientSocket.send(offer.encode())

            elif type == protocol.MessageType.OFFER:
                print("Peer received P2P chat request")
                ip= rp.body.decode()
                #rp.body.decode().split(":")
                #ip= ip_port[0]
                #port= int(ip_port[1])
                print("Ready to start chat.")
                peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peerSocket.connect((ip, peerPort))
                #start_chat()
        except Exception as e:
            print("Error: reply not received.", e)
            break
            

"""Sends messages to peer."""
def send_message(username):
    while True:  # Loops to send messages to different peers
        peerUsername = input("Enter peer username or 'exit' to quit: ")
        if peerUsername.lower() == "exit":
            break
        try:
            send_request(clientSocket, username, peerUsername)
        except Exception as e:
            print("Error: P2P request not sent.", e)
            break

        """ 
        Code to send actual messages
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect((peerUsername, peerPort))
            print("Connection successful.")
            while True:  # Loops to send messages to the same peer
                try:
                    message = input("Enter message or 'exit' to change peers: ")
                    if message.lower() == "exit":
                        peerSocket.close()
                        break
                    elif message.startswith("media "):
                        file_path = message.split(" ", 1)[1]
                        with open(file_path, "rb") as f:
                            chunk = f.read(chunkSize)
                            #while chunk:
                                #mediaSendSocket.sendto(chunk, (peerUsername, mediaPort))
                                #chunk = f.read(chunkSize)
                    else:
                        msg = ProtocolUtils(
                        headers={
                            "messageType": protocol.MessageType.CHAT,
                            "message": protocol.Messages.TEXT,
                            "sender": "peer",
                            "recipient": peerUsername},
                             body= message.encode())
                        peerSocket.send(msg.encode())        
                except:
                    print("Error: message not sent.")
                    peerSocket.close()
                    break
        except:
            print("Connection unsuccessful.") """

"""Receives messages from peer and prints them to the console."""
def receive_peer_connections(listenSocket):
    while True:  # Loops to accept connection and message from different peers
        try:
            new_socket, new_address = listenSocket.accept()
            threading.Thread(target=handle_peer_connection, args=(new_socket,), daemon=True).start()
        except:
            print("Error: failed to accept peer connection.")
            break

def handle_peer_connection(peerSocket):
    while True:  # Loops to receive messages from the same peer
        try:
            message = peerSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
            if not message:
                print("Peer disconnected.")
                break
            else:
                msg = ProtocolUtils.ProtocolUtils.decode(message)
                print(f"[Peer]: {msg.body.decode()}")
        except:
            print("Error: failed to receive message from peer.")
            break
    peerSocket.close() 

#must still add UDP for media transfer, and p2p connection handling (peer discovery, connection setup, etc.)


if __name__ == '__main__':
    login_result = loginToServer()
    if login_result is None:
        print("Cannot continue without login.")
        exit()
    else:
        username, clientSocket = login_result

    # Start UDP media receiver
    #threading.Thread(target=receive_media, args=(udpRecvSocket,), daemon=True).start()

    # Ask user if connecting to peer or server
    choice = input("Connect to server or peer? (s/p): ").lower()
    if choice == "s":
        send_request(clientSocket, username)
    elif choice == "p":
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listenSocket.bind(("0.0.0.0", peerPort))
        listenSocket.listen()
        threading.Thread(target=receive_peer_connections, args=(listenSocket,), daemon=True).start()
        send_message(username)