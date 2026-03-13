"""Sends and recieves"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GroupMembershipManager import GroupMembershipManager
from ClientConnectionManager import ClientConnectionManager

import random   # going to use random peer port sockets and media port sockets
import socket
import threading
import protocol
from ProtocolUtils import ProtocolUtils

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500
peerPort = 1600
mediaPort = 1700  # for sending media files, UDP_port
chunkSize = 6000  # bytes per UDP packet
mediaSocket = None
incoming_media = {}
incoming_media_lock = threading.Lock()
printLock = threading.Lock()
peerConnections = {}  # dictionary of client and sockets
peerMediaConnections = {}
listenSocket = None
p2p_Listening = False  # flag to indicate if client is currently listening for p2p connection
chatRequests = {}  # dictionary of usernames who sent requests
groupMembers = {}  # dictionary of group memberships
groupChats = []  # list of group chats the client is connected to

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

def registerOrLogin(clientSocket):
    attempt_count = 0
    print("-----------------------------")
    print("Welcome to Chat-Chat!")
    while True:
        print("(L)ogin existing user")
        print("(R)egister new user")
        print("(Q)uit")
        choice = input("Please select your option (l/r/q): ").strip()

        if choice.lower() == 'q':
            print("Exiting...")
            clientSocket.close()
            return None

        username = input("\nEnter username: ").strip()
        password = input("Enter password: ").strip()

        if not username or not password:
            print("Username and password cannot be empty.")
            continue
        if len(username) > 30:
            print("Username too long, max 30 characters.")
            continue

        if choice.lower() == "l":
            successful = False
            while attempt_count != 3 and not successful:
                if attempt_count>0:  # Only ask for credentials again if this is a retry
                    print(f"\nAttempt {attempt_count + 1} of 3")
                    username = input("Enter username: ").strip()
                    password = input("Enter password: ").strip()   
                login_msg = ProtocolUtils(
                    headers={
                        "MessageType": protocol.MessageType.COMMAND,
                        "Message": protocol.Messages.LOGIN,
                        "Sender": username,
                        "Recipient": serverAddress,
                        "Username": username,
                        "Password": password,
                        "PeerPort": str(peerPort)
                    },
                    body=b""
                    )
                clientSocket.send(login_msg.encode())
            
                # Wait for server reply
                replyBytes = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
                if not replyBytes:
                    print("Server disconnected.")
                    clientSocket.close()
                    return None
            
                reply = ProtocolUtils.decode(replyBytes)
                if reply.message == protocol.Messages.ACK:
                    print(f"\nLogin successful!")
                    return (username, clientSocket)
                elif reply.message == protocol.Messages.ERROR:
                    attempt_count+=1
                    print(f"\nLogin failed: {reply.body.decode().strip()}")
                
                    if attempt_count <3:
                        retry = input(f"Try again? {3-attempt_count} tries remaining (y/n): ")
                        if retry != 'y':
                            clientSocket.close()
                            return None
                    else:
                        print("Cannot continue without login.")
                        clientSocket.close()
                        return None
                        
        elif choice.lower() == "r":
             # validate strength using the connection manager helper
             is_valid, errorMsg = ClientConnectionManager.is_password_strong(password)

             if not is_valid:
                 print(f"Password too weak. {errorMsg}\n")
                 continue
             
             register_msg = ProtocolUtils(
                 headers={
                     "MessageType": protocol.MessageType.COMMAND,
                     "Message": protocol.Messages.REGISTER,  # Add this to protocol.Messages
                     "Sender": username,
                     "Recipient": serverAddress,
                     "Username": username,
                     "Password": password,
                     "PeerPort": str(peerPort)
                 },
                 body=b""
             )
             clientSocket.send(register_msg.encode())
            
            # Wait for server reply
             replyBytes = clientSocket.recv(4096)
             if not replyBytes:
                print("Server disconnected.")
                clientSocket.close()
                return None
            
             reply = ProtocolUtils.decode(replyBytes)
             if reply.message == protocol.Messages.ACK:
                print(f"{reply.body.decode().strip()} Proceeding to login...")
                
                # After successful registration, automatically proceed to login
                login_msg = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.COMMAND,
                            "Message": protocol.Messages.LOGIN,
                            "Sender": username,
                            "Recipient": serverAddress,
                            "Username": username,
                            "Password": password,
                            "PeerPort": str(peerPort),
                            "MediaPort": str(mediaPort)
                        },
                        body=b""
                    )
                clientSocket.send(login_msg.encode())
                    
                replyBytes = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
                if not replyBytes:
                        print("Server disconnected.")
                        clientSocket.close()
                        return None
                    
                reply = ProtocolUtils.decode(replyBytes)
                if reply.message == protocol.Messages.ACK:
                        print(f"Login successful!")
                        return (username, clientSocket)
                else:
                        print(f"Login failed after registration: {reply.body.decode()}")
                        return None
               
             elif reply.message == protocol.Messages.ERROR:
                print(f"Registration failed: {reply.body.decode().strip()}")
                retry = input("Try again? (y/n): ").lower()
                if retry != 'y':
                    clientSocket.close()
                    return None
        else:
            print("Invalid choice. Please enter 'l', 'r', or 'q'.")

def loginToServer():  # client must login to server
    global peerPort, mediaPort
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        clientSocket.connect((serverAddress, serverPort))
        print("Server connection successful.")
    except Exception as e:
        print("Error: Server connection failed.")
        return None
    
    peerPort = random.randint(1600,1700)
    mediaPort = random.randint(1701,1800)
    return registerOrLogin(clientSocket)

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
            rep = clientSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
            if not rep:
                print("Server disconnected.")
                break
            
            rp = ProtocolUtils.decode(rep)
            type= rp.message_type

            if type == protocol.MessageType.P2P_REQ:
                 requester = rp.sender
                 print(f"\n{requester} wants to chat")
                 chatRequests[requester] = rp
            
            elif rp.message == protocol.Messages.ERROR:
                    with printLock:
                        print(f"\nChat request failed: {rp.body.decode().strip()}")

            elif type == protocol.MessageType.CONTROL and rp.message == protocol.Messages.CHAT_INFO:
                decoded_body = rp.body.decode().strip()
                members = decoded_body.split(",")                  
                group_name = rp.headers.get("Recipient")
                groupMembers[group_name] = members

                if group_name not in groupChats:
                    groupChats.append(group_name)
                
                with printLock:
                    print(f"\nYou are now connected to: {group_name}")
                    print(f"Members: {', '.join(members)}")

            if rp.message == protocol.Messages.GROUP_TEXT:
                sender = rp.sender
                text = rp.body.decode().strip()
                
                with printLock:
                    sys.stdout.write("\r" + " " * 80 + "\r")
                    sys.stdout.write(f"[{sender}]: {text}\n")  # group message
                    sys.stdout.write(f"[{username}]: ")  # redisplay prompt
                    sys.stdout.flush()           

            elif type == protocol.MessageType.P2P_OFFER:
                with printLock:
                    print(f"\n{rp.sender} received chat request")
                ip_port = rp.body.decode().strip()
                parts= ip_port.split(":")
                ip = parts[0]
                port = int(parts[1])

                if len(parts)>= 3:
                    peer_media_port = int(parts[2])
                else:
                    peer_media_port = 1700

                p_username = rp.sender
                peerMediaConnections[p_username] = peer_media_port

                with printLock:
                    print(f"Connecting to {p_username}...")

                try:
                   peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                   peerSocket.connect((ip, port))

                   #send ack to method handle_peer_connection, this is the last step of the p2p connection setup, once peer receives this ack, it will start the chat thread to listen for messages from this peer
                   ack_msg = ProtocolUtils(
                       headers={
                           "MessageType": protocol.MessageType.CONTROL,
                           "Message": protocol.Messages.ACK,
                           "Sender": username,
                           "Recipient": p_username
                       },
                       body=str(mediaPort).encode() #send to media port, for file transefer acknowlangements
                   )
                   peerSocket.send(ack_msg.encode())

                   peerConnections[p_username] = peerSocket
                   # Start chat thread
                   p2p_thread = threading.Thread(
                       target=handle_p2p_chat, 
                       args=(peerSocket, p_username, username), 
                       daemon = True
                    )
                   p2p_thread.start()
                   
                   with printLock:
                       print(f"Connected to {p_username}! Please select option 3 to chat or option 4 to exchange files.")

                except Exception as e:
                     with printLock:
                        print(f"Failed to connect to peer: {e}")
                    
        except Exception as e:
            with printLock:
                print(f"Failed to connect to peer: {e}")


def accept_request(clientSocket, username, requester, peerPort):
        accept_msg = ProtocolUtils(
            headers={
                "MessageType": protocol.MessageType.P2P_OFFER,
                "Message": protocol.Messages.CHAT_ACCEPT,
                "Sender": username,
                "Recipient": requester
            },
            body= f"{serverAddress}:{peerPort}:{mediaPort}".encode())
        
        try:
            clientSocket.send(accept_msg.encode())
            print(f"Accepted chat request from {requester}.")
        except Exception as e:
            print("Error: failed to send accept message.", e)

def receive_peer_connections():
    while True:  # Loops to accept connection from different peers
        try:
            new_socket, new_address = listenSocket.accept()  # Waits for incoming connections
            hpc_thread =threading.Thread(target=handle_peer_connection, args=(new_socket,), daemon=True)
            hpc_thread.start()
        except:
            with printLock:
                print("Error: failed to accept peer connection.")
            break
   
"""Sends Messages to peer."""
def send_message(username, p_username, mess):
    if p_username in peerConnections:
        try:
            msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.CHAT,
                    "Message": protocol.Messages.TEXT,
                    "Sender": username,
                    "Recipient": p_username},
                body= mess.encode())
            
            peerConnections[p_username].send(msg.encode())
        except Exception as e:
            print("Error: Peer message not sent.", e)

def receive_media():  # UDP
    global mediaSocket
    # print("Receiver listening on:", mediaPort)
    while True:
        try:
            data, addr = mediaSocket.recvfrom(65536)
            mess = ProtocolUtils.decode(data)
            if mess.sender == username:
                continue

            if mess.message == protocol.Messages.MEDIA:
                sender = mess.sender
                recipient = mess.recipient
                file = mess.headers.get("File")  # this can come from #kwargs in the protocol header
                NumChunks = int(mess.headers.get("TotalChunks"))
                chunkIndex = int(mess.headers.get("ChunkIndex"))
                chunkData = mess.body

                keys = (sender, file)
                with incoming_media_lock:
                    if keys not in incoming_media:
                        incoming_media[keys] = {
                            'totalChunks': NumChunks,
                            'chunks' : [None]*NumChunks,
                            'file' : [None]
                        }
                    entry = incoming_media[keys]
                    entry['chunks'][chunkIndex] = chunkData

                    # checks if all chunks received, cause UDP is unreliable
                    if all (chunk is not None for chunk in entry['chunks']):
                        completeData = b''.join(entry['chunks'])  # put chunks together and save
                        FileBase, FileExt = os.path.splitext(file)  # new file to prevent overriidng,[FileBase.FileExt]
                        save_name = f"received_{sender}_{FileBase}{FileExt}"

                        with open(save_name, 'wb') as f:
                            f.write(completeData)
                        print(f"\nReceived file '{file}' from {sender}, saved as {save_name}" )
                        del incoming_media[keys]

        except Exception as e:
            print(f"[Media receive Error]{e}")
                 
def send_media(username, p_username, filePath):
    if p_username not in peerConnections:
        print("Not connected to that peer.")
        return
    
    try: # getting IP from TCP socket
        peerSocket = peerConnections[p_username]
        peerIP = peerSocket.getpeername()[0]
        # peerAddress = (peerIP, mediaPort)
        peerUDPPort = peerMediaConnections[p_username]
        peerAddress = (peerIP, peerUDPPort)

        # reading file and splitting to chunks
        with open(filePath, 'rb') as f:
            fileData = f.read()
        NumChunks = (len(fileData)+chunkSize-1)//chunkSize
        fileName = os.path.basename(filePath)

        print(f"Sending '{fileName}' to {p_username} ({NumChunks} chunks. . .)")

        for i in range(NumChunks):
            start = i*chunkSize
            end = start+chunkSize
            chunk = fileData[start:end]

            headers = {
                "MessageType": protocol.MessageType.DATA,
                "Message": protocol.Messages.MEDIA,
                "Sender": username,  
                "Recipient": p_username,
                "File": fileName,
                "TotalChunks": str(NumChunks),
                "ChunkIndex": str(i)
             }
            mess = ProtocolUtils(headers=headers, body=chunk)
            mediaSocket.sendto(mess.encode(), peerAddress)
        print(f"File '{fileName}' sent successfully.")
        print("Sending UDP to:", peerIP, peerUDPPort)
        
    except FileNotFoundError:
        print("File not Found.")
    except Exception as e:
        print(f"Error sending media: {e}")


def handle_peer_connection(peerSocket):
    while True:  # loops to receive Messages from the same peer
        try:
            msg_bytes = peerSocket.recv(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)
            if not msg_bytes:
                print("Peer disconnected.")
                return

            msg = ProtocolUtils.decode(msg_bytes)

            if msg.message == protocol.Messages.ACK:
                peer_username = msg.sender
                peerConnections[peer_username] = peerSocket

                try:
                    peer_media_port = int(msg.body.decode())
                    peerMediaConnections[peer_username] = peer_media_port
                except:
                    peerMediaConnections[peer_username] = 1700
                
                print(f"Connected to {peer_username}! Please select option 3 to chat or option 4 to exchange files.")

                hc_thread = threading.Thread(target=handle_p2p_chat, 
                                args=(peerSocket, peer_username, username), daemon=True)
                hc_thread.start()
                return
        except:
            print("Error: failed to receive Message from peer.")

"""waits for user input"""
def chat_with_peer(username, p_username):  # dedicated mode for chatting

    if p_username not in peerConnections:
        print("Not connected to that peer.")
        return
    
    chatMode = True

    with printLock:
        print(f"\nChatting with {p_username} (type 'quit' to end chat)\n")
   
    # handles sending
    while chatMode:
        try:
            message = input(f"[{username}]: ")
            if message.lower() == "quit":
                break
            
            if message.strip():  # this checks if message is not just whitespace
                send_message(username, p_username, message)  # this is for individual chats

        except Exception as e:
            print("Error: Failed to send message to peer.", e)
            break
    
    print(f"\nChat with {p_username} ended")

    # clean up
    if p_username in peerConnections:
        del peerConnections[p_username]

"""constantly waits for network msgs"""
def handle_p2p_chat(peerSocket, p_username, username):
    while True:  # receiving loop
        try:
            mess = peerSocket.recv(1024)

            if not mess:
                print(f"{p_username} disconnected.")
                break
            else:
                msg = ProtocolUtils.decode(mess)
                if msg.message == protocol.Messages.TEXT:  # sending actual p2p texts
                    if msg.headers.get("Sender") == username:
                        continue
                    text =  msg.body.decode().strip()
                    with printLock:
                        sys.stdout.write("\r" + "" * 80 + "\r")  # clears current input line
                        sys.stdout.write(f"[{p_username}]: {text}")
                        sys.stdout.write(f"\n[{username}]: ")  # redraw prompt       

        except Exception as e:
            print("Error: failed to receive Message from peer.", e)
            break

    # disconnecting from peer
    print(f"\nDisconnected from {p_username}")
    if p_username in peerConnections:
        del peerConnections[p_username] # remove from peerConnections
    try:
        peerSocket.close()
    except Exception as e:
        pass
        
def chat_with_group(group_name):  # handles sending
    with printLock:
        print(f"\nChatting with {group_name} (type 'quit' to end)\n")

    chatMode = True
    while chatMode:
        try:
            message = input(f"[{username}]: ")
            if message.lower() == "quit":
                with printLock:
                    sys.stdout.write("\r" + " " * 80 + "\r")
                    print(f"\nEnding chat with {group_name}.")
                chatMode = False
                break

            group_msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.DATA,
                    "Message": protocol.Messages.GROUP_TEXT,
                    "Sender": username,
                    "Recipient": group_name,
                },
                body=message.encode(),
            )
            try:
                clientSocket.send(group_msg.encode())

            except Exception as e:
                print("Error: Failed to send message to group chat.", e)
                break
        except Exception as e:
            print("Error: Failed.", e)
            break

    threading.current_thread().in_group_chat = False  # updates flag
    print(f"\nChat with {group_name} ended.")

if __name__ == '__main__':
    while True:
        login_result = loginToServer()
        if login_result is None:
            exit()
            break
        else:
            username, clientSocket = login_result
            listen_for_p2p()
            rpc_thread =threading.Thread(target=receive_peer_connections, daemon=True)
            rpc_thread.start()
            rr_thread = threading.Thread(target=receive_reply, 
                        args=(clientSocket, username), daemon=True)
            rr_thread.start()
            """threading.Thread(target=handle_group_chat, 
                 args=(clientSocket, username), 
                 daemon=True).start()"""
            mediaSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mediaSocket.bind(("0.0.0.0", mediaPort))
            threading.Thread(target=receive_media
                             , daemon=True).start()
            break

flag = True

manager = GroupMembershipManager()
# the actual server interactions here
while flag:
    with printLock:
        print("\nOptions:")
        print("1. Send chat request to peer")
        print("2. Accept/ reject chat request")
        print("3. Send text to connected peer")
        print("4. Send media to connected peer")
        print("5. Create group")
        print("6. Join group")
        print("7. Leave group")
        print("8. Send group chat request to server")
        print("9. Send message to group chat")
        print("10. Logout")
    option = input("\nEnter option number: ")

    if option == "1":
        target = input("Enter username to chat with: ")
        try:
            send_request(clientSocket, username, target)
        except:
            print ("Error sending request")
    
    elif option == "2":
        if chatRequests:
            print("Pending chat requests:")
            for requester in chatRequests.keys():
                print(f"- {requester}")
            selected = input("\nEnter username of request to respond to: ")
            if selected in chatRequests:
                choice = input(f"Accept chat request from {selected}? (y/n): ")
                if choice.lower() == "y":
                    accept_request(clientSocket, username, selected, peerPort)
                    del chatRequests[selected]
                else:
                    # Send rejection
                    reject_msg = ProtocolUtils(
                        headers={
                            "MessageType": protocol.MessageType.P2P_OFFER,
                            "Message": protocol.Messages.CHAT_REJECT,
                            "Sender": username,
                            "Recipient": selected
                        },
                    body=b""
                    )
                    clientSocket.send(reject_msg.encode())
                    print(f"Chat request from {selected} rejected.")
                    del chatRequests[selected]
            else:
                print("Invalid selection.")
        else:
            print("No chat requests at the moment")

    elif option == "3":
        if peerConnections:
            print("Connected peers:")
            for peer in peerConnections.keys():
                print(f"- {peer}")
            target = input("Enter username to chat with: ")
            if target in peerConnections:
                # enter p2p chat
                chat_with_peer(username, target)
            else:
                print("Not connected to that peer.")
        else:
            print("No connected peers")

    elif option == "4":
        if peerConnections:
            print("Connected peers:")
            for peer in peerConnections.keys():
                 print(f"- {peer}")
            target = input("Enter username to send media: ")
            if target in peerConnections:
                 filepath = input("Enter path to media file: ")
                 send_media(username, target, filepath)
            else:
              print("Not connected to that peer.")
        else:
            print("No connected peers.")

    elif option == "5":
        group_name = input("Enter group name: ")
        print(GroupMembershipManager.createGroup(manager, group_name, username))  # send create group request to server

    elif option == "6":
        group_name = input("Enter group name to join: ")
        if(GroupMembershipManager.groupExists(manager, group_name)):
            print(GroupMembershipManager.joinGroup(manager, group_name, username))  # send join group request to server

    elif option == "7":
        group_name = input("Enter group name to leave: ")
        print(GroupMembershipManager.leaveGroup(manager, group_name, username))  # send leave group request to server

    elif option == "8":
        group_name = input("Enter group name to connect with: ")  # need to connect before able to chat
        if(GroupMembershipManager.groupExists(manager, group_name)):
            if (GroupMembershipManager.getUserInGroup(manager, group_name, username)):
                # request group member list from server
                group_info_request = ProtocolUtils(
                    headers={
                        "MessageType": protocol.MessageType.CONTROL,
                        "Message": protocol.Messages.CHAT_INFO,
                        "Sender": username,
                        "Recipient": group_name
                    },
                    body=b""
                )
                try:
                    clientSocket.send(group_info_request.encode())
                    print(f"Connecting to group {group_name}. Please select option 9 to chat with a group.")  # send msg to server     
                except Exception as e:
                    print(f"Failed to send group request: {e}")
            else:
                with printLock:
                    print(f"[{username} not in {group_name}.] You cannot send messages to a group you are not a part of.")
        else:
            with printLock:
                    print("Group does not exist.")

    # will show connections for different groups (NOT membership)
    elif option == "9":
        if groupChats:
            print("Available group chats:")
            for gc in groupChats:
                with printLock:
                    print(f"- {gc}")
            group_name = input("Enter groupchat to chat with: ")
            if group_name in groupChats:
                with printLock:
                    print(f"\n{group_name} members: ")  # prints group members
                for m in groupMembers[group_name]:
                    with printLock:
                        print(f"- {m}")
                chat_with_group(group_name)  # start chat
            else:
                print("Group name not found in your connected groups.")
        else:
            print("No group chats available. Use option 8 to connect to a group first.")

    elif option == "10":
    # send logout request to server and close socket
        logout_msg = ProtocolUtils(
        headers={
            "MessageType": protocol.MessageType.COMMAND,
            "Message": protocol.Messages.LOGOUT,
            "Sender": username,
            "Recipient": serverAddress
        },
        body=b""
        )
        clientSocket.send(logout_msg.encode())
        rpc_thread.join()
        rr_thread.join()

        clientSocket.close()
        listenSocket.close()
        flag = False
        with printLock:
            print("Logged out.")
    else:
        print("Invalid choice")
        
exit()    
