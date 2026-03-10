import threading
import uuid
import os

"""
    issue with group management
    leaving and joining groups are fine, 
    if the goup is empty (no members)
    and someone joins the group, 
    the first entry is ",EchoCat" instead of just "EchoCat"

    Still nothing going to server but the group management is working
    in the groupData.txt

    Therefore it is only the sending msgs at the moment
"""
class GroupMembershipManager:  
  def __init__(self, dataFile="serverData/groupData.txt"):
        self.dataFile = dataFile
        self.groups = {} #groupID: {name, members}
        self.lock = threading.Lock()

        os.makedirs("serverData", exist_ok=True)
        if not os.path.exists(self.dataFile):
            open(self.dataFile, "w").close()     

  def createGroup(self, groupName, creator):
        with self.lock:     #thread safety
            if not os.path.exists(self.dataFile):
                return "File does not exist."
            
            if self.groupExists(groupName):
                return "Group name already exists."
            
            groupID = str(uuid.uuid4())[:8]  #short unique ID

            with open(self.dataFile, "a") as f:
                f.write(f"{groupID}:{groupName}:{creator}\n")
                return f"Group '{groupName}' created with ID {groupID}."
            
            return "Some other error occured"            #testing
        
  def joinGroup(self, groupName, username):
        with self.lock:
            if not self.groupExists(groupName):
                return "Group name does not exist."
            with open(self.dataFile, "r") as f:
                lines = f.readlines()
            with open(self.dataFile, "w") as f:
                for line in lines:
                    parts = line.strip().split(":")

                    groupID = parts[0]
                    name = parts[1]
                    members = parts[2]

                    if name == groupName:
                        membersList = members.split(",")
                        if username in membersList:
                            f.write(line)
                            return f"{username} is already in {groupName}"

                        membersList.append(username)
                        newMembers = ",".join(membersList)

                        newLine = f"{groupID}:{name}:{newMembers}\n"

                        f.write(newLine)
                    else:
                        f.write(line)
            return f"User '{username}' joined group {groupName}."

  def leaveGroup(self, groupName, username):
            with self.lock:
                if not self.groupExists(groupName):
                    return "Group name does not exist."
                #remove user from group in file (simplified, could be optimized)
                with open(self.dataFile, "r") as f:
                    lines = f.readlines()
                with open(self.dataFile, "w") as f:
                    for line in lines:
                        parts = line.strip().split(":")

                        groupID = parts[0]
                        name = parts[1]
                        members = parts[2]

                        if name == groupName:
                            membersList = members.split(",")
                            if username not in membersList:
                                f.write(line)
                                return f"{username} is not in {groupName}"

                            membersList.remove(username)
                            newMembers = ",".join(membersList)

                            newLine = f"{groupID}:{name}:{newMembers}\n"

                            f.write(newLine)
                        else:
                            f.write(line)
            return f"User '{username}' left group {groupName}."

  def groupExists(self, groupName):
        with open(self.dataFile, "r") as f:
            for line in f:
                _, name, _ = line.strip().split(":")
                if name == groupName:
                    return True
        return False
  
  def groupIDExists(self, groupID):
        with open(self.dataFile, "r") as f:
            for line in f:
                id, _, _ = line.strip().split(":")
                if id == groupID:
                    return True
        return False
  
  def getGroupCreator(self, groupName):
       if(GroupMembershipManager.groupExists(self, groupName)):
        with open(self.dataFile, "r") as f:
            for line in f:
                _, _, creator = line.strip().split(":")
                if creator != None:
                    return creator
