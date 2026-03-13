#helper class to track client connections
import os
import threading

"""handles file storage for usernames and groups"""
class ClientConnectionManager:
    def __init__(self, dataFile="serverData"):
        self.clients = []  # track clients by username
        self.client_info = {}  # track client info by socket
        self.lock = threading.Lock()  # lock for thread safety
        self.dataFile = dataFile 

        os.makedirs(dataFile, exist_ok=True)
        self.usernameFile = os.path.join(dataFile, "usernames.txt") # file to store usernames
    
    # user registration and login
    def register(self, username, password):
        with self.lock:
            while self.usernameExists(username):
                print("Username already taken, please try again.")

            with open(self.usernameFile, "a") as f:
                f.write(f"{username}:{password}\n")  # add counter at later stage

            return True, "Registration successful."
                
    def authenticate(self, username, password):
        with self.lock:
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
    
    @staticmethod
    def is_password_strong(password):
        # basic strength requirements
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least 1 uppercase letter."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least 1 lowercase letter."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least 1 number."
        
        return True, "Password good!"  # password meets all criteria
