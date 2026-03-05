"""handles connections"""
import socket
import threading
import os
import protocol     #protocol module
import ProtocolUtils #protocol utils for encoding/decoding messages

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500

clientSockets = []          #track connected clients

"""handle individual client connections"""
def handle_client(clientSocket): 
    try:
        #receiving msg
        while True:
            msg = clientSocket.recv(1042).decode()    #receive
            if not msg:     #empty msg = client disconnected
                break

            broadcast(msg, clientSocket)

    except Exception as e:
            print("Error with client: {}".format(e))
        
    clientSocket.close()
    if clientSocket in clientSockets:
        clientSockets.remove(clientSocket)

"""broadcast to all except sender"""
def broadcast(msg, senderSocket):
    for sock in clientSockets[:]:   #iterate over copy of list (safer)
        if sock != senderSocket:
            try:
                sock.send(msg)
            except:
                if sock in clientSockets:
                    clientSockets.remove(sock)      #remove failed conns

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

        thread =threading.Thread(target=handle_client, args=(clientSocket,))
        thread.daemon = True        #thread closes when main program exits.
        thread.start()


#healper class to track client connections
#handles file storage for usernames and groups
class ClientConnectionManager:
    def __init__(self, dataFile="defultStr"):
        self.clients = [] #track clients by username
        self.client_info = {} #track client info by socket
        self.lock = threading.Lock() #lock for thread safety
        self.dataFile = dataFile 
        self.usernameFile = os.path.join(dataFile, "usernames.txt") #file to store usernames
    
    #user registration and login
    def register(self, username, pasword):
        with self.lock:
            if self.usernameExists(username):
                with open(self.usernameFile, "a") as f:
                    f.write(f"{username +('_1')}:{pasword}\n")  #add counter at later stage
                return True, "Registration successful."
            with open(self.usernameFile, "a") as f:
                f.write(f"{username}:{pasword}\n")
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



    #active session management
    def addClient(self, socket, username):
        with self.lock:
            if username in self.clients:
                username += "_1" #simple way to avoid duplicates, could be improved
            self.clients.append(username)
            self.client_info[socket] = {"username": username}
            print(f"Client {username} connected.")

if __name__ == "__main__":
    start_server()