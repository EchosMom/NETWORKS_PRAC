#helper class to track client connections
import os
import threading

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
    def register(self, username, password):
        with self.lock:
            if self.usernameExists(username):
                username = username + "_1"

            with open(self.usernameFile, "a") as f:
                f.write(f"{username}:{password}\n")  #add counter at later stage

            return True, "Registration successful."
                
    def authenticate(self, username, password):
        with self.lock:
            print("Username file path:", self.usernameFile)
            if not os.path.exists(self.usernameFile):
                return False, "User not found"
            
            with open(self.usernameFile, "r") as f:
                for line in f:
                    stored_username, stored_password = line.strip().split(":")
                    if stored_username == username and stored_password == password:
                        return True, "Login successful"
        return False, "Invalid username or password"
    
    def usernameExists(self, username):
        if not os.path.exists(self.usernameFile):
            return False
        
        with open(self.usernameFile, "r") as f:
            for line in f:
                if line.split(":")[0] == username:
                    return True
        return False
