"""Sends and recieves"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from GroupMembershipManager import GroupMembershipManager

import socket
import threading
import protocol
from ProtocolUtils import ProtocolUtils

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500
peerPort = 1600
mediaPort = 1700 #this is for sending media files, UDP_port
chunkSize = 65536 #bytes per UDP packet

peerConnections = {} #track peer connections - username -> socket
listenSocket = None
p2p_Listening = False #flag to indicate if client is currently listening for p2p connection
chatRequests = {} #track incoming chat requests - list of usernames who sent requests
global accepted #track p2p accepts
accepted = False

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

#UDP sockets
#mediaSendSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#mediareceiveSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#mediareceiveSocket.bind(("0.0.0.0", mediaPort))

#client must login to server
def loginToServer():
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        clientSocket.connect((serverAddress, serverPort))
        print("Server connection successful.")
    except Exception as e:
        print("Error: Server connection failed.")
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
            print(f"Login successful")  # removed {reply.body.decode()} 
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
    clientSocket.send(request.encode())     #msg ent in byte form to the clientSocket to the peer
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
                 print(f"\n[P2P Request] {requester} wants to chat")
                 chatRequests[requester] = rp                 

            elif rp.message == protocol.Messages.GROUP_TEXT:
                sender = rp.sender
                text = rp.body.decode()
                print(f"\n[Group message from {sender}]: {text}")

            elif type == protocol.MessageType.P2P_OFFER:
                print("Peer received P2P chat request")
                ip_port = rp.body.decode().strip()
                ip= ip_port.split(":")[0]
                port = int(ip_port.split(":")[1])
                p_username = rp.sender

                print(f"\n[P2P] Connecting to {p_username} at {ip}:{port}")

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
                       body=b""
                   )
                   peerSocket.send(ack_msg.encode())

                   peerConnections[p_username] = peerSocket
                   # Start chat thread
                   threading.Thread(target=handle_p2p_chat, args=(peerSocket, p_username)).start()
                   print(f"Connected to {p_username}! You can now chat.")
                   # global accepted
                   # accepted = True   

                except Exception as e:
                     print(f"Failed to connect to peer: {e}")
                    
        except Exception as e:
              print(f"Failed to connect to peer: {e}")
            
def accept_request(clientSocket, username, requester, peerPort):
    
        accept_msg = ProtocolUtils(
            headers={
                "MessageType": protocol.MessageType.P2P_OFFER,
                "Message": protocol.Messages.CHAT_ACCEPT,
                "Sender": username,
                "Recipient": requester
            },
            body= f"127.0.0.1:{peerPort}".encode())
        try:
            clientSocket.send(accept_msg.encode())
            print(f"Chat request from {requester} accepted. Waiting for connection.")
            if not p2p_Listening:
                listen_for_p2p()
                threading.Thread(target=receive_peer_connections, daemon=True).start()

        except Exception as e:
            print("Error: failed to send accept message.", e)

def receive_peer_connections():
    while True:  # Loops to accept connection and Message from different peers
        try:
            new_socket, new_address = listenSocket.accept()  # Waits for incoming connections
            threading.Thread(target=handle_peer_connection, args=(new_socket,), daemon=True).start()
        except:
            print("Error: failed to accept peer connection.")
            break
   
"""Sends Messages to peer."""
def send_message(p_username, mess):
    if username in peerConnections:
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
            print("Error: Message not sent.", e)
                 


def handle_peer_connection(peerSocket):
    # while True:  # Loops to receive Messages from the same peer
    try:
        Message = peerSocket.recv(1024)
        if not Message:
            print("Peer disconnected.")
            # break
        
        msg = ProtocolUtils.decode(Message)
        peer_username = msg.sender
        if msg.message == protocol.Messages.ACK:
            #if peer_username != username:
            peerConnections[peer_username] = peerSocket
            print(f"\n[P2P] Connected to {peer_username}")
        threading.Thread(target=handle_p2p_chat, args=(peerSocket, peer_username)).start()

    except:
        print("Error: failed to receive Message from peer.")
        # break
    """peerSocket.close() """

def chat_with_peer( p_username): #dedicated mode for chatting

    if p_username not in peerConnections:
        print("Not connected to that peer.")
        return
    
    # does not check if other peer (target peer is connected)

    peerSocket = peerConnections[p_username]
    print(f"\n[P2P] Chatting with {p_username}. Type 'quit' to end.")
    chatMode = True

    #inner method to receive messages from peer while in chat mode
    
    """def receive_in_chat():
        while chatMode:
            try:
                mess = peerSocket.recv(1024)
                if not mess:
                    print(f"{p_username} disconnected.")
                    break
                else:
                    msg = ProtocolUtils.decode(mess)
                    if msg.message == protocol.Messages.TEXT: #sending actual texts p2p
                        print(f"\n[{p_username}]: {msg.body.decode()}")
            except Exception as e:
                print("Error: failed to receive Message from peer.", e)
                break
    

    recveive_thread = threading.Thread(
        target=handle_p2p_chat,
        args=(peerSocket, p_username),
        daemon=True
    )    
    recveive_thread.start()"""

        #loop for chat
    while chatMode:
        try:
            message = input("You: ")
            if message.lower() == "quit":
                    print(f"\n[P2P] Ending chat with {p_username}.")
                    break     

            send_message(p_username, message)

        except Exception as e:
                print("Error: failed to send Message to peer.", e)
                break
    print(f"\n[P2P] Chat with {p_username} ended.")     

def handle_p2p_chat(peerSocket, p_username):
    while True:
        try:
            mess = peerSocket.recv(1024)
            if not mess:
                print(f"{p_username} disconnected.")
                break
            else:
                msg = ProtocolUtils.decode(mess)
                sender = msg.sender
                if msg.message == protocol.Messages.TEXT: #sending actual texts p2p
                    print(f"\n[{sender}]: {msg.body.decode()}")
        except Exception as e:
            print("Error: failed to receive Message from peer.", e)
            break
    #disconnecting from peer, remove from peerConnections

    print(f"\n[P2P] Disconnected from {p_username}")
    if p_username in peerConnections:
        del peerConnections[p_username]
    try:
        peerSocket.close()
    except Exception as e:
        pass


#must still add UDP for media transfer, and p2p connection handling (peer discovery, connection setup, etc.)


if __name__ == '__main__':
    while True:
        login_result = loginToServer()
        if login_result is None:
            print("Cannot continue without login.")
            tryAgain= input("Try again? (y/n): ")
            if tryAgain.lower() == "n":
                exit()
                break
        else:
            username, clientSocket = login_result
            listen_for_p2p()
            threading.Thread(target=receive_peer_connections, daemon=True).start()
            threading.Thread(target=receive_reply, 
                        args=(clientSocket, username), daemon=True).start()
            break

flag = True

manager = GroupMembershipManager()
# the actual server interactions here
print("You are interacting with server.")
while True:
    while flag:
        print("Options:")
        print("1. Send chat request to peer")
        print("2. Accept/ reject chat request")
        print("3. Chat with connected peer")
        print("4. Create group")
        print("5. Join group")
        print("6. Leave group")
        print("7. Send group message")
        print("8. Logout")

        option = input("Enter option number: ")

        if option == "1":
            target = input("Enter username to chat with: ")
            try:
                send_request(clientSocket, username, target)
            except:
                print ("Error sending request")
            """if accepted == True:
                message = input("Type your messages (type 'quit' to end): ")
                if message == "quit":
                    break
                send_message(target, message)"""
        
        elif option == "2":
            if chatRequests:
                print("Pending chat requests:")
                for requester in chatRequests.keys():
                    print(f"- {requester}")
                selected = input("Enter username of request to respond to: ")
                if selected in chatRequests:
                    choice = input(f"Accept chat request from {selected}? (y/n): ")
                    if choice.lower() == "y":
                        accept_request(clientSocket, username, selected, peerPort) # removed chatRequests[selected]
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

        elif option == "3": #sending actual messages
            if peerConnections:
                print("Connected peers:")
                for peer in peerConnections.keys():
                    print(f"- {peer}")
                target = input("Enter username to chat with: ")
                if target in peerConnections:
                   #enter p2p chat
                    chat_with_peer(target)
                else:
                    print("Not connected to that peer.")
            else:
                print("No connected peers")

        elif option == "4":
            group_name = input("Enter group name: ")
            print(GroupMembershipManager.createGroup(manager, group_name, username)) #send create group request to server

        elif option == "5":
            group_name = input("Enter group name to join: ")
            if(GroupMembershipManager.groupExists(manager, group_name)):
                print(GroupMembershipManager.joinGroup(manager, group_name, username)) #send join group request to server

        elif option == "6":
            group_name = input("Enter group name to leave: ")
            print(GroupMembershipManager.leaveGroup(manager, group_name, username)) #send leave group request to server

        elif option == "7":
            group_name = input("Enter group name to send message to: ")
            if(GroupMembershipManager.groupExists(manager, group_name)):
                message = input("Enter message: ")
            group_msg = ProtocolUtils(
                headers={
                    "MessageType": protocol.MessageType.DATA,
                    "Message": protocol.Messages.GROUP_TEXT,
                    "Sender": username,
                    "Recipient": group_name
                },
                body=message.encode()
            )

            clientSocket.send(group_msg.encode())
            print("Group message sent to server.")            #send group message request to server

        elif option == "8":
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

            clientSocket.send(logout_msg.encode())
            print("Logged out.")
            clientSocket.close()
            listenSocket.close()
            peerConnections.close()
            flag = False
        else:
            print("Invalid choice")

    exit()

    

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
        
  
    