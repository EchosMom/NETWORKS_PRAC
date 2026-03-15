"""handles connections"""
import socket
import threading

import sys
import os
# add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ClientConnectionManager
import protocol
from ProtocolUtils import ProtocolUtils  # protocol utils for encoding/decoding messages


serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500             

clientSockets = []  # track connected clients
clientInfo = {}  # track clients with info - socket -> usrname, p2p_port, public_ip}

"""handle individual client connections"""
def handle_client(clientSocket, manager): 
    try:
        # receiving msg
        while True:
            data = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
                               
            if not data:  # empty msg = client disconnected
                break
            
            try:
                mess = ProtocolUtils.decode(data)
                msg_type = mess.message_type
                msg_content = mess.message
                # login handling
                if mess.message == protocol.Messages.LOGIN:
                    username = mess.headers.get("Username")
                    password = mess.headers.get("Password")
                    peer_port = mess.headers.get("PeerPort")
                    udp_port = mess.headers.get("MediaPort")

                    if clientSocket in clientInfo:
                        clientInfo[clientSocket]["peer_port"] = peer_port
                        clientInfo[clientSocket]["MediaPort"] = udp_port

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
                    print(f"Sending login reply to {username}, auth_success={auth_success}")
                    clientSocket.send(reply.encode())
                    continue
                
                if msg_content == protocol.Messages.REGISTER:
                    username = mess.headers.get("Username")
                    password = mess.headers.get("Password")
                    response, message = manager.register(username, password)
                    if response == True:
                        reply = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.CONTROL,
                                "Message": protocol.Messages.ACK,
                                "Sender": "server",
                                "Recipient": username
                            },
                            body=message.encode()
                        )
                    else:
                        reply = ProtocolUtils(
                            headers={
                                "MessageType": protocol.MessageType.CONTROL,
                                "Message": protocol.Messages.ERROR,
                                "Sender": "server",
                                "Recipient": username
                            },
                            body=message.encode()
                        )
                    clientSocket.send(reply.encode())

                    continue

                if msg_content == protocol.Messages.LOGOUT:
                    disconnect_client(clientSocket)
                    break

                if msg_content == protocol.Messages.GET_PEER_UDP_INFO:
                    target = mess.body.decode()

                    for sock, info in clientInfo.items():
                        if info.get("username") ==  target:
                            peer_info = ProtocolUtils(
                              headers={
                               "MessageType": protocol.MessageType.CONTROL,
                               "Message": protocol.Messages.PEER_UDP_INFO,
                               "Sender": "server",
                               "Recipient": mess.sender   
                              },
                              body=f"{info['address'][0]}:{info.get('udp_port',1700)}".encode()
                            )
                            clientSocket.send(peer_info.encode())
                            break

                if msg_content == protocol.Messages.GROUP_MEDIA_META:
                    group_name = mess.headers.get("Recipient")
                    filename = mess.headers.get("FileName")
                    filesize = mess.headers.get("FileSize")
                    filehash = mess.headers.get("FileHash")
                    sender = mess.sender
                     # Store metadata temporarily
                        # Then forward to group members
                   # prep_group_media_transfer(group_name, sender, filename, filesize, filehash)

                if msg_content == protocol.Messages.GROUP_MEDIA_CHUNK:
                    group_name = mess.headers.get("Recipient")
                    filename = mess.headers.get("FileName")
                    chunk_index = int(mess.headers.get("ChunkIndex"))
                    total_chunks = int(mess.headers.get("TotalChunks"))
                    chunk_data = mess.body
                    sender = mess.sender
                    # Forward chunk to all group members
                    forward_media_to_target(group_name, sender, filename, chunk_index, total_chunks, chunk_data)

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

    # find targets socket
    targetSocket = None  # initialise

    for sock, info in clientInfo.items():
        if info.get("username") == target_usr:
            targetSocket = sock
            break

    if targetSocket:  # not empty
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
        print(f"Forwarded P2P request from {requestor_usr} to {target_usr}")  # prints in the server terminal        

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
        print(f"Failed to forward P2P request from {requestor_usr} to {target_usr}")        

       
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

def forward_media_to_target(groupName, sender, filename, chunk_index, total_chunks, chunk_data):
    print(f"DEBUG: Forwarding {filename} chunk {chunk_index+1}/{total_chunks} to group {groupName}")

    members = getOnlineMember(groupName)
    print(f"DEBUG: Online members in {groupName}: {members}")

    if not members:  #works safely with empty list
        print(f"DEBUG SERVER: No online members in group {groupName}")
        return

    for m in members:
        if m !=sender:
            for sock, info in clientInfo.items():
                if info.get("username") == m:
                    chunkMess = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.DATA,
                            "Message": protocol.Messages.GROUP_MEDIA_CHUNK,
                            "Sender": sender,
                            "Recipient": m,
                            "FileName": filename,
                            "TotalChunks": str(total_chunks),
                            "ChunkIndex": str(chunk_index),
                            "GroupName": groupName
                        },
                        body=chunk_data
                    )
                    try:
                        sock.send(chunkMess.encode())
                        print(f"Forwarded media to {groupName}")
                    except Exception as e:
                        print(f"Error media message to {groupName}: ", e)
                    break




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
                        members.append(m)  # add members to send message list
    except Exception as e:
        return f"Error reading groupData.txt: {e}"

    for sock, info in clientInfo.items():  # all connected clients
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
                print(f"Forwarded group message from {sender} to {username}")
            except Exception as e:
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
                        members.append(m)
                    if sender not in members:
                        members.append(sender)                    
    except:
        return "Hmm... something went wrong"
    
    # find sender socket
    sender_socket = None
    for sock, info in clientInfo.items():
        if info.get("username") == sender:
            sender_socket = sock
            break

    if sender_socket is None:
        return (f"Error: {sender} is not online.")
    
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
    
def getOnlineMember(groupName):
     members = []
     try:
        with open("serverData/groupData.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3 and parts[1] == groupName:
                    mems = parts[2].strip().split(",")
                    print(f"DEBUG SERVER: All members in {groupName}: {mems}")
                    for m in mems:
                        # Check if member is online
                        for info in clientInfo.values():
                            if info.get("username") == m:
                                members.append(m)
                                print(f"DEBUG SERVER: {m} is online")
                                break
                    break
     except Exception as e:
        print(f"DEBUG SERVER: Error in getOnlineMember: {e}")
    
     print(f"DEBUG SERVER: Returning members: {members}")
     return members  # Always returns a list (empty if none found)

"""remove connected clients"""
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

    manager = ClientConnectionManager.ClientConnectionManager( dataFile = "serverData")  # manage clients and data

    while True:  # server always-on
        clientSocket, clientAddress = serverSocket.accept()
        print("New connection from {}:{}".format(clientAddress[0], clientAddress[1]))

        clientSockets.append(clientSocket)

        # store client address information
        clientInfo[clientSocket] = {
            "address": clientAddress,
            "username": None,  # will be set after login
            "MediaPort": 1501
        }

        thread = threading.Thread(
            target=handle_client, 
            args=(clientSocket,manager),
            daemon = True
        )
        thread.start()

if __name__ == "__main__":
    start_server()
