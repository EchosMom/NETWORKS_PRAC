"""handles connections"""
import socket
import threading
import os
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
            data = clientSocket.recv(1042).decode()    #receive
            if not data:     #empty msg = client disconnected
                break
            
            #parse json msg
            try:
                mess = json.loads(data)
                msg_type = mess.get("type")

                #noraml chat msg
                if msg_type == protocol.MessageType.CHAT:
                    broadcast(data, clientSocket)

                elif msg_type == protocol.MessageType.P2P_REQ:
                    handle_p2p_req(clientSocket, mess)

                elif msg_type == protocol.MessageType.P2P_OFFFER:
                    forward_to_target(mess)

                elif msg_type == protocol.MessageType.P2P_ICE:
                    forward_to_target(mess)
                
                #login handling
                elif msg_type == protocol.Messages.LOGIN:
                    username = mess.get("username")
                    clientInfo[clientSocket]["username"] = username
                    print(f"{username} logged in")

            except json.JSONDecodeError:
                broadcast(data, clientSocket)
            

    except Exception as e:
            print("Error with client: ", e)
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

    manager = ClientConnectionManager( dataFile = "serverData") #manage clients and data

    while True:     #server always-on
        clientSocket, clientAddress = serverSocket.accept()
        print("New connection from {}:{}".format(clientAddress[0], clientAddress[1]))

        clientSockets.append(clientSocket)

        #store client adress info
        clientInfo[clientSocket] = {
            "address": clientAddress,
            "username": None            #will be set after login
        }

        thread = threading.Thread(target=handle_client, args=(clientSocket,))
        thread.daemon = True        #thread closes when main program exits.
        thread.start()


#helper class to track client connections
"""handles file storage for usernames and groups"""
class ClientConnectionManager:
    def __init__(self, dataFile="serverData"):
        self.clients = [] #track clients by username
        self.client_info = {} #track client info by socket
        self.lock = threading.Lock() #lock for thread safety
        self.dataFile = dataFile 

        os.makedirs(dataFile, exist_ok=True)
        self.usernameFile = os.path.join(dataFile, "usernames.txt") #file to store usernames
    
    #user registration and login
    def register(self, username, pasword):
        with self.lock:
            if self.usernameExists(username):
                username = username + "_1"

            with open(self.usernameFile, "a") as f:
                f.write(f"{username}:{pasword}\n")  #add counter at later stage

            return True, "Registration successful."
                
    def authenticate(self, username, password):
        with self.lock:
            if not os.path.exists(self.usernameFile):
                return False
            
            with open(self.usernameFile, "r") as f:
                for line in f:
                    stored_username, stored_password = line.strip().split(":")
                    if stored_username == username and stored_password == password:
                        return True
        return False
    
    def usernameExists(self, username):
        if not os.path.exists(self.usernameFile):
            return False
        
        with open(self.usernameFile, "r") as f:
            for line in f:
                if line.split(":")[0] == username:
                    return True
        return False

if __name__ == "__main__":
    start_server()