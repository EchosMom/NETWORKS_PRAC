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
serverPort = 1500               # chatgpt says to use protocol.Protocol.TCP_PORT

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
                if msg_type == protocol.MessageType.CHAT:
                    broadcast(mess.encode(), clientSocket)

                if msg_type == protocol.MessageType.P2P_REQ:
                    handle_p2p_req(clientSocket, mess)

                if msg_type == protocol.MessageType.P2P_OFFER:
                    forward_to_target(mess)

                if msg_type == protocol.MessageType.P2P_ICE:
                    forward_to_target(mess)

                if msg_content == protocol.Messages.GROUP_TEXT:
                    groupID = mess.headers.get("Recipient")   
                    text = mess.body.decode()                 
                    sender = mess.sender                      
                    send_group_message(groupID, sender, text) 

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
    targetSocket = None

    for sock, info in clientInfo.items():
        if info.get("username") == target_usr:
            targetSocket = sock
            break

    if targetSocket:
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
       
"""forward p2p conn data to target client"""
def forward_to_target(mess):
    target_usr = mess.recipient
    for sock, info in clientInfo.items():
        if info.get("username") == target_usr:
            try:
                sock.send(mess.encode())
            except Exception as e:
                print(f"Error forwarding message to {target_usr}: ", e)
            break

"""broadcast to all except sender"""
def broadcast(msg, senderSocket):
    for sock in clientSockets[:]:   #iterate over copy of list (safer)
        if sock != senderSocket:
            try:
                sock.sendall(msg)
            except:
                disconnect_client(sock) #remove failed conns

"""find group members and send msg to each member socket"""
def send_group_message(groupID, sender, text):
    members = []
    try:
        with open("groupData.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if parts[0] == groupID:
                    members.append(parts[-1])   # username
    except:
        return

    for sock, info in clientInfo.items():
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
            except:
                disconnect_client(sock)


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
        }

        thread = threading.Thread(target=handle_client, args=(clientSocket,manager))
        thread.daemon = True        #thread closes when main program exits.
        thread.start()

if __name__ == "__main__":
    start_server()
## ClientConnectionManager class moved to its own file for better organization, see ClientConnectionManager.py
