"""handles connections"""
import socket
import threading

import sys
import os
# add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ClientConnectionManager
import protocol  #protocol module
from ProtocolUtils import ProtocolUtils    #protocol utils for encoding/decoding messages


serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500             

clientSockets = []          #track connected clients
clientInfo = {}             #track clients with info - socket -> usrname, p2p_port, public_ip}

"""handle individual client connections"""
def handle_client(clientSocket, manager): 
    try:
        #receiving msg
        while True:
            data = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)    #receive
                               
            if not data:     #empty msg = client disconnected
                break
            
            try:
                mess = ProtocolUtils.decode(data)
                msg_type = mess.message_type
                msg_content = mess.message
                
                #login handling
                if mess.message == protocol.Messages.LOGIN:
                    username = mess.headers.get("Username")
                    password = mess.headers.get("Password")
                    peer_port = mess.headers.get("PeerPort")

                    if clientSocket in clientInfo:
                        clientInfo[clientSocket]["peer_port"] = peer_port

                    auth_success, response = manager.authenticate(username, password)

                    if auth_success:
                        clientInfo[clientSocket]["username"] = username
                        reply = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.CONTROL,
                                "Message": protocol.Messages.ACK,
                                "Sender": "server",
                                "Recipient": username
                            },
                            body=response.encode()
                        )
                    else:
                        reply = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.CONTROL,
                                "Message": protocol.Messages.ERROR,
                                "Sender": "server",
                                "Recipient": username
                            },
                            body=response.encode()
                        )
                    clientSocket.send(reply.encode())
                    continue
                
                #noraml chat msg
                #if msg_type == protocol.MessageType.CHAT:
                    #broadcast(mess.encode(), clientSocket)

                if msg_type == protocol.MessageType.P2P_REQ:
                    handle_p2p_req(clientSocket, mess)

                if msg_type == protocol.MessageType.P2P_OFFER:
                    forward_to_target(mess)

                if msg_type == protocol.MessageType.P2P_ICE:
                    forward_to_target(mess)

                if msg_content == protocol.Messages.GROUP_TEXT:
                    groupName = mess.headers.get("Recipient")   
                    text = mess.body.decode()                 
                    sender = mess.sender                      
                    send_group_message(groupName, sender, text) 

                if msg_content == protocol.Messages.CHAT_INFO:
                    groupName = mess.headers.get("Recipient")   
                    sender = mess.sender                      
                    getMembers(groupName, sender)

            except Exception as e:
                print("Error handling client message: ", e)
    except Exception as e:
        print("Error processing message: ", e)
    finally:
        disconnect_client(clientSocket)

"""handle p2p request"""
def handle_p2p_req(requestor_socket, mess):
    target_usr = mess.headers.get("Recipient")
    requestor_usr = mess.headers.get("Sender")

    #find targets socket
    targetSocket = None         #initialise

    for sock, info in clientInfo.items():
        if info.get("username") == target_usr:
            targetSocket = sock
            break

    if targetSocket:        #not empty
        forward_msg = ProtocolUtils(
            headers={
                "MessageType": protocol.MessageType.P2P_REQ,    
                "Message": protocol.Messages.CHAT_REQUEST,      
                "Sender": requestor_usr,                        
                "Recipient": target_usr                         
            },
            body=mess.body                                      
        )

        targetSocket.send(forward_msg.encode())    
        print(f"Forwarded P2P request from {requestor_usr} to {target_usr}")    # happens in the server terminal        

    else:
        error_msg = ProtocolUtils(
            headers={
            "MessageType": protocol.MessageType.CONTROL,
            "Message":  protocol.Messages.ERROR,
            "Sender": "server",
            "Recipient": requestor_usr
            },
            body=b"User not online"
        )
        requestor_socket.send((error_msg).encode())
        print(f"Failed to forward P2P request from {requestor_usr} to {target_usr}")    # happens in the server terminal        

       
"""forward p2p conn data to target client"""
def forward_to_target(mess):
    target_usr = mess.recipient
    sender_usr = mess.sender

    for sock, info in clientInfo.items():
        if info.get("username") == target_usr and target_usr != sender_usr:
            try:
                sock.send(mess.encode())
                print(f"Forwarded P2P offer to {target_usr}")
            except Exception as e:
                print(f"Error forwarding message to {target_usr}: ", e)
            break

"""broadcast to all except sender UNUSED METHOD
def broadcast(msg, senderSocket):
    for sock in clientSockets[:]:   #iterate over copy of list (safer)
        if sock != senderSocket:
            try:
                sock.sendall(msg)       #seems off
            except:
                disconnect_client(sock) #remove failed conns
"""

"""find group members and sends msgs to those online"""
def send_group_message(groupName, sender, text):
    members = []
    try:
        with open("serverData/groupData.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if parts[1] == groupName:
                    mems = parts[2].strip().split(",")
                    for m in mems:
                        members.append(m)   # usernames in group
    except Exception as e:
        return f"Error reading groupData.txt: {e}"

    for sock, info in clientInfo.items():       #all connected clients
        username = info.get("username")
        if username in members and username != sender:
            msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.DATA,
                    "Message": protocol.Messages.GROUP_TEXT,
                    "Sender": sender,
                    "Recipient": username
                },
                body=text.encode()
            )
            try:
                sock.send(msg.encode())
                print(f"DEBUG: msg sent to {username}")
            except:
                print(f"DEBUG: msg failed to send to {username}: {e}")
                disconnect_client(sock)
            
"""sends list of online group membbers to sender"""
def getMembers(groupName, sender):
    members = []
    try:
        with open("serverData/groupData.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if parts[1] == groupName:
                    mems = parts[2].strip().split(",")
                    for m in mems:
                        members.append(m)   # usernames in group
                    if sender not in members:
                        members.append(sender)                    
    except:
        return "Hmm... something went wrong"
    
    #find sender scoket
    sender_socket = None
    for sock, info in clientInfo.items():
        if info.get("username") == sender:
            sender_socket = sock
            break
    
        str_members = ",".join(members)

        msg = ProtocolUtils(
            headers={
                "MessageType": protocol.MessageType.CONTROL,
                "Message": protocol.Messages.CHAT_INFO,
                "Sender": "server",
                "Recipient": groupName
            },
            body=str_members.encode()
        )
        try:
            sender_socket.send(msg.encode())
            return f"Group members sent to {sender}"
        except:
            disconnect_client(sender_socket)
            return f"Error: Cannot send group member list to {sender}"
    else:
        return f"Error: {sender} is not online"


"""remove disconnected clients"""
def disconnect_client(sock):
    if sock in clientSockets:
        clientSockets.remove(sock)

    if sock in clientInfo:
        username = clientInfo[sock].get("username")
        print(f"{username} disconnected")
        del clientInfo[sock]

    try:
        sock.close()
    except:
        pass

"""start chat server"""
def start_server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
    serverSocket.bind((serverAddress, serverPort))
    serverSocket.listen()

    print("Server is listening on {}:{}".format(serverAddress, serverPort))

    manager = ClientConnectionManager.ClientConnectionManager( dataFile = "serverData") #manage clients and data

    while True:     #server always-on
        clientSocket, clientAddress = serverSocket.accept()
        print("New connection from {}:{}".format(clientAddress[0], clientAddress[1]))

        clientSockets.append(clientSocket)

        #store client adress info
        clientInfo[clientSocket] = {
            "address": clientAddress,
            "username": None,            #will be set after login
            "UDP_PORT": 1501              # add udp port for p2p
            #"peer_port": None
        }

        thread = threading.Thread(
            target=handle_client, 
            args=(clientSocket,manager),
            daemon = True
        )
        thread.start()

if __name__ == "__main__":
    start_server()
## ClientConnectionManager class moved to its own file for better organization, see ClientConnectionManager.py
