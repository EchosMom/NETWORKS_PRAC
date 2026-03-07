"""Sends and recieves"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import GroupMembershipManager

import socket
import threading
import protocol
from ProtocolUtils import ProtocolUtils

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500
peerPort = 1600
mediaPort = 1700 #this is for sending media files, UDP_port
chunkSize = 65536 #bytes per UDP packet

peerConnections = {} #track peer connections - username -> (ip, port)
listenSocket = None
p2p_Listening = False #flag to indicate if client is currently listening for p2p connection

def listen_for_p2p():
    global p2p_Listening, listenSocket
    if p2p_Listening:
        print("Already listening for P2P connections.")
        return
    listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listenSocket.bind(("0.0.0.0", peerPort))
    listenSocket.listen(5)
    p2p_Listening = True
    print(f"Listening for P2P connections on port {peerPort}...")

def accept_Connections ():
    global p2p_Listening, listenSocket
    while p2p_Listening:
        try:
            peersoclket, peerAddress = listenSocket.accept()
            print(f"New connection from {peerAddress}")
            threading.Thread(target=handle_peer_connection, args=(peersoclket,), daemon=True).start()
        except Exception as e:
            print("Error: failed to accept peer connection.", e)
            break
    threading.Thread(target=accept_Connections, daemon=True).start()
    return listenSocket

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

    login_msg = ProtocolUtils(
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
        replyBytes = clientSocket.recv(4096)
        if not replyBytes:
            print("Server disconnected.")
            clientSocket.close()
            return None
        
        reply = ProtocolUtils.decode(replyBytes)
        if reply.message == protocol.Messages.ACK:
            print(f"Login successful: {reply.body.decode()}")
            listen_for_p2p()
            threading.Thread(target=receive_reply, 
                           args=(clientSocket, usernameInput), daemon=True).start()
            return (usernameInput, clientSocket)
             
        if reply.message == protocol.Messages.ERROR:
            print(f"Login failed: {reply.body.decode()}")
            clientSocket.close()
            return None

"""Sends requests to the server."""
def send_request(clientSocket, username, recipient):
    request = ProtocolUtils(
        headers={
            "MessageType": protocol.MessageType.P2P_REQ,
            "Message": protocol.Messages.CHAT_REQUEST,
            "Sender": username,
            "Recipient": recipient
        },
        body=b""
    )
    clientSocket.send(request.encode())
    print(f"Chat request sent to {recipient}")


"""Receives replies from the server and prints them to the console."""
def receive_reply(clientSocket, username):
    while True:
        try:
            reply = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
            if not reply:
                print("Server disconnected.")
                break
            rp = ProtocolUtils.decode(reply)
            type= rp.message_type
            if type == protocol.MessageType.P2P_REQ:
                 requester = rp.sender
                 print(f"\n[P2P Request] {requester} wants to chat")
                 response = input("Accept? (y/n): ")

                 if response.lower() == "y":
                        accept_msg = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.P2P_OFFER,
                                "Message": protocol.Messages.CHAT_ACCEPT,
                                "Sender": username,
                                "Recipient": requester},
                            body= f"127.0.0.1:{peerPort}".encode())
                        clientSocket.send(accept_msg.encode())


                 else:
                        reject_msg = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.P2P_OFFER,
                                "Message": protocol.Messages.CHAT_REJECT,
                                "Sender": username,
                                "Recipient": requester},
                            body=b"")
                        clientSocket.send(reject_msg.encode())

            elif type == protocol.MessageType.P2P_OFFER:
                print("Peer received P2P chat request")
                ip= rp.body.decode().split(":")[0]
                port = int(rp.body.decode().split(":")[1])
                p_username = rp.sender

                print(f"\n[P2P] Connecting to {p_username} at {ip}:{port}")

                print("Ready to start chat.")
                peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peerSocket.connect((ip, port))
                peerConnections[p_username] = peerSocket
               # Start chat thread
                threading.Thread(target=handle_p2p_chat, 
                                   args=(peerSocket, p_username), daemon=True).start()
                    
                print(f"Connected to {p_username}! You can now chat.")
                print("Type your messages (type 'quit' to end):")
                    
        except Exception as e:
                    print(f"Failed to connect to peer: {e}")
        except Exception as e:
            print("Error: reply not received.", e)
            break
            

"""Sends Messages to peer."""
def send_Message(username, mess):
    if username in peerConnections:
        try:
            msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.CHAT,
                    "Message": protocol.Messages.TEXT,
                    "Sender": 'Me',
                    "Recipient": username},
                body= mess.encode())
            
            peerConnections[username].send(msg.encode())
        except Exception as e:
            print("Error: Message not sent.", e)

    
                
""" 
        Code to send actual messages
            peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peerSocket.connect((peerUsername, peerPort))
            print("Connection successful.")
            while True:  # Loops to send Messages to the same peer
                try:
                    Message = input("Enter Message or 'exit' to change peers: ")
                    if Message.lower() == "exit":
                        peerSocket.close()
                        break
                    elif Message.startswith("media "):
                        file_path = Message.split(" ", 1)[1]
                        with open(file_path, "rb") as f:
                            chunk = f.read(chunkSize)
                            while chunk:
                                mediaSendSocket.sendto(chunk, (peerIP, mediaPort))
                                chunk = f.read(chunkSize)
                        mediaSendSocket.sendto(b"__END__", (peerIP, mediaPort))
                    else:
                        msg = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.CHAT,
                            "Message": protocol.Messages.TEXT,
                            "Sender": username,
                            "Recipient": peerIP},
                             body= Message.encode())
                        peerSocket.send(msg.encode())        
                except:
                    print("Error: Message not sent.")
                    peerSocket.close()
                    break
        except:
            print("Connection unsuccessful.") """

"""Receives Messages from peer and prints them to the console."""
def receive_peer_connections(listenSocket):
    while True:  # Loops to accept connection and Message from different peers
        try:
            new_socket, new_address = listenSocket.accept()
            threading.Thread(target=handle_peer_connection, args=(new_socket,), daemon=True).start()
        except:
            print("Error: failed to accept peer connection.")
            break

def handle_peer_connection(peerSocket):
    while True:  # Loops to receive Messages from the same peer
        try:
            Message = peerSocket.recv(1024)
            if not Message:
                print("Peer disconnected.")
                break
            else:
                msg = ProtocolUtils.decode(Message)
                if msg.message == protocol.Messages.ACK:
                 peer_username = msg.sender
                 peerConnections[peer_username] = peerSocket
                 print(f"\n[P2P] Connected to {peer_username}")
                
                
                threading.Thread(target=handle_p2p_chat, 
                               args=(peerSocket, peer_username), daemon=True).start()
        except:
            print("Error: failed to receive Message from peer.")
            break
    """peerSocket.close() """


def handle_p2p_chat(peerSocket, p_username):
 while True:
        try:
            mess = peerSocket.recv(1024)
            if not mess:
                print(f"{p_username} disconnected.")
                break
            else:
                msg = ProtocolUtils.decode(mess)
                if msg.message == protocol.Messages.TEXT:
                     print(f"\n[{p_username}]: {msg.body.decode()}")
        except:
            break
 print(f"\n[P2P] Disconnected from {p_username}")
 if p_username in peerConnections:
        del peerConnections[p_username]

"""peerSocket.close()"""

#must still add UDP for media transfer, and p2p connection handling (peer discovery, connection setup, etc.)


if __name__ == '__main__':
    login_result = loginToServer()
    if login_result is None:
        print("Cannot continue without login.")
        exit()
    else:
        username, clientSocket = login_result

choice = input("Would you like to interact with the server or a peer? (s/p): ").lower()
if choice == "s":#t actual server interactions here
        print("Interacting with server./n")
        print("Options:")
        print("1. Send chat request to peer")
        print("2. Create group")
        print("3. Join group")
        print("4. Leave group")
        print("5. Send group message")
        print("6. Logout")
        print("7. Exit")

        while True:
            option = input("Enter option number: ")

            if option == "1":
                target = input("Enter username to chat with: ")
                send_request(clientSocket, username, target)
                break
            elif option == "2":
                 group_name = input("Enter group name: ")
                 GroupMembershipManager.createGroup(group_name, username) #send create group request to server
                 break
         
            elif option == "3":
                 group_name = input("Enter group name to join: ")
                 GroupMembershipManager.joinGroup(group_name, username) #send join group request to server
                 break
           
            elif option == "4":
                 group_name = input("Enter group name to leave: ")
                 GroupMembershipManager.leaveGroup(group_name, username) #send leave group request to server
                 break
            elif option == "5":
                 group_name = input("Enter group name to send message to: ")
                 message = input("Enter message: ")
                 break
            #send group message request to server
            elif option == "6":
            #send logout request to server and close socket
                 logout_msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.COMMAND,
                    "Message": protocol.Messages.LOGOUT,
                    "Sender": username,
                    "Recipient": serverAddress
                },
                body=b""
        )
                 break
        clientSocket.send(logout_msg.encode())
        print("Logged out.")
        clientSocket.close()
        exit()
        
elif choice == "p":
         target = input("Enter username to chat with: ")
         send_request(clientSocket, username, target)
    

    # Start UDP media receiver
    #threading.Thread(target=receive_media, args=(udpRecvSocket,), daemon=True).start()
    #
'''def receive_media():
        filename = "received_media.bin"   
        file = open(filename, "wb")       
        print("Receiving media...")

        while True:
            data, addr = mediareceiveSocket.recvfrom(chunkSize)
            if data == b"__END__":        
                break
            file.write(data)              
        file.close()
        print(f"Media saved to {filename}")  '''
        
    # Ask user if connecting to peer or server
    