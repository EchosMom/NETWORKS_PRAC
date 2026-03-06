"""handles connections"""
import socket
import threading

import sys
import os
# add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ClientConnectionManager
import protocol         #protocol module
import ProtocolUtils    #protocol utils for encoding/decoding messages
import json             #for structured msgs

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500               # chatgpt says to use protocol.Protocol.TCP_PORT

clientSockets = []          #track connected clients
clientInfo = {}             #track clients with info - socket -> usrname, p2p_port, public_ip}

"""handle individual client connections"""
def handle_client(clientSocket): 
    try:
        #receiving msg
        while True:
            data = clientSocket.recv(1042)    #receive
                               
            if not data:     #empty msg = client disconnected
                break
            
            
        try:
            mess = ProtocolUtils.decode(data)
            msg_type = mess.messageType
            msg_content = mess.message

            #noraml chat msg
            if msg_type == protocol.MessageType.CHAT:
                broadcast(mess.encode, clientSocket)

            elif msg_type == protocol.MessageType.P2P_REQ:
                handle_p2p_req(clientSocket, mess)

            elif msg_type == protocol.MessageType.P2P_OFFFER:
                forward_to_target(mess)

            elif msg_type == protocol.MessageType.P2P_ICE:
                forward_to_target(mess)
            
            #login handling
            elif msg_type == protocol.Messages.LOGIN:
                username = mess.headers.get("Username")
                password = mess.headers.get("Password")
                auth_success = ClientConnectionManager.authenticate(username, password)

                if auth_success:
                    clientInfo[clientSocket]["username"] = username
                    print(f"{username} logged in")
                    reply = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.COMMAND,
                            "Message": protocol.Messages.ACK,
                            "Sender": "server",
                            "Recipient": username
                        },
                        body=b"Login successful."
                    )
                else:
                    print(f"Failed login attempt for user: {username}")
                    reply = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.COMMAND,
                            "Message": protocol.Messages.ERROR,
                            "Sender": "server",
                            "Recipient": username
                        },
                        body=b"Invalid username or password."
                    )
            clientSocket.send(reply.encode())
            
        except Exception as e:
            print("Error handling client message: ", e)
    except Exception as e:
        print("Error processing message: ", e)
    finally:
        disconnect_client(clientSocket)

"""handle p2p request"""
def handle_p2p_req(requestor_socket, mess):
    target_usr = mess.get("target")
    requestor_usr = mess.get("from")

    #find targets socket
    targetSocket = None

    for sock, info in clientInfo.items():
        if info.get("username") == target_usr:
            targetSocket = sock
            break

    if targetSocket:
        response = {
            "type": protocol.MessageType.P2P_REQ,
            "from": requestor_usr,
            "data": mess.get("data", {})
        }
        targetSocket.send(json.dumps(response).encode())

    else:
        error_msg = {
            "type": protocol.MessageType.P2P_REJ,
            "reason": "User not online"
        }
        requestor_socket.send(json.dumps(error_msg).encode())

"""forward p2p conn data to target client"""
def forward_to_target(mess):
    target_usr = mess.get("to")
    for sock, info in clientInfo.items():
        sock.send(json.dumps(mess).encode())
        return

"""broadcast to all except sender"""
def broadcast(msg, senderSocket):
    for sock in clientSockets[:]:   #iterate over copy of list (safer)
        if sock != senderSocket:
            try:
                sock.send(msg)
            except:
                disconnect_client(sock) #remove failed conns
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

        thread = threading.Thread(target=handle_client, args=(clientSocket,))
        thread.daemon = True        #thread closes when main program exits.
        thread.start()

if __name__ == "__main__":
    start_server()
## ClientConnectionManager class moved to its own file for better organization, see ClientConnectionManager.py
