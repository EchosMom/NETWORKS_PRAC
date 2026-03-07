import threading
import uuid
import os

class GroupMembershipManager:
  
  def __init__(self, dataFile="groupData.txt"):
        self.dataFile = dataFile
        self.groups = {} #groupID: {name, members}
        self.lock = threading.Lock()
        
  def createGroup(self, groupName, creator):
        with self.lock:
            if not os.path.exists(self.dataFile):
                return False
            if self.groupExists(groupName):
                return False, "Group name already exists."
            groupID = str(uuid.uuid4())[:8]  #short unique ID
            with open(self.dataFile, "a") as f:
                f.write(f"{groupID}:{groupName}:{creator}\n")
            return True, f"Group '{groupName}' created with ID {groupID}."
        
  def joinGroup(self, groupID, username):
        with self.lock:
            if not self.groupIDExists(groupID):
                return False, "Group ID does not exist."
            with open(self.dataFile, "a") as f:
                f.write(f"{groupID}:{username}\n")
            return True, f"User '{username}' joined group {groupID}."
        
  def leaveGroup(self, groupID, username):
            with self.lock:
                if not self.groupIDExists(groupID):
                    return False, "Group ID does not exist."
                #remove user from group in file (simplified, could be optimized)
                lines = []
                with open(self.dataFile, "r") as f:
                    lines = f.readlines()
                with open(self.dataFile, "w") as f:
                    for line in lines:
                        if line.strip() != f"{groupID}:{username}":
                            f.write(line)
                return True, f"User '{username}' left group {groupID}."

  def groupExists(self, groupName):
        with open(self.dataFile, "r") as f:
            for line in f:
                _, name, _ = line.strip().split(":")
                if name == groupName:
                    return True
        return False