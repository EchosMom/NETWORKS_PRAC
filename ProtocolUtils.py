#this file adds usability to the protocol.py
import protocol

class ProtocolUtils:

    def __init__(self, headers=None, body=b''):
        self.headers = headers or {}
        self.body = body
    
    @property
    def messageType(self):
        return self.headers.get("MessageType")
    
    @property
    def message(self):
        return self.headers.get("Message")
    
    @property
    def sender(self):
        return self.headers.get("Sender")
    
    @property
    def recipient(self):
        return self.headers.get("Recipient")
    
    def encode(self):
        #convert bytes for sending
        return protocol.Protocol.encodeMessage(self.messageType, self.message, self.sender, Recipient=self.recipient, body=self.body,**{k: v for k, v in self.headers.items() if k not in ["MessageType", "Message", "Sender", "Recipient"]})

    @classmethod
    def decode(cls, data):
        #convert bytes to usable format
        headers, body = protocol.Protocol.decodeMessage(data)
        return cls(headers, body)
    
    #helper methods to check message type for impotant messages like text or media
    def is_text(self):
        return self.message == protocol.Messages.TEXT
    def is_group_text(self):
        return self.message == protocol.Messages.GROUP_TEXT
    def is_media(self):
        return self.message == protocol.Messages.MEDIA
    def is_group_media(self):
        return self.message == protocol.Messages.GROUP_MEDIA
    def is_chat_request(self):
        return self.message == protocol.Messages.CHAT_REQUEST
    def is_login(self):
        return self.message == protocol.Messages.LOGIN
    def is_error(self):
        return self.message == protocol.Messages.ERROR


class ProtocolHandler:
#handlesparsing incoming messages, esentially messge prosesing
    def __init__(self, clientManager, groupManager):
        self.clientManager = clientManager
        self.groupManager = groupManager

    def handle_message(self, data, clientSocket):
        message = ProtocolUtils.decode(data)
        #process message based on type and content, for example:
        if message.is_login():
            username = message.headers.get("Username")
            password = message.headers.get("Password")
            success, response = self.clientManager.authenticate(username, password)
            replyType = protocol.Messages.ACK if success else protocol.Messages.ERROR
            reply = ProtocolUtils(headers={"MessageType": replyType, "Message": response}, body=b"").encode()
            clientSocket.send(reply)
        elif message.is_text():
            recipient = message.recipient
            text = message.body.decode()  #assuming body is bytes
            #send text to recipient using client manager to find their socket, etc.

    def handleCommand(self, message, clientSocket):
        #this method would contain the logic to process different message types and perform actions like routing messages, managing groups, etc.
        command = message.headers.get("Message")
        sender = message.sender

        if command == protocol.Messages.LOGIN:
            username = message.headers.get("Username")
            password = message.headers.get("Password")
            success, response = self.clientManager.register(username, password)
            replyType = protocol.Messages.ACK if success else protocol.Messages.ERROR
            reply = ProtocolUtils(headers={"MessageType": replyType, "Message": response}, body=b"").encode()
            clientSocket.send(reply)
        #elif command == protocol.Messages.CHAT_REQUEST:
            #request to start a p2p connection
            #recipient = message.headers.get("Recipient")
            #### must still add P2P connection logic here, this is just a placeholder for now
            #self.handle_p2p_req(clientSocket, message)

    def handleData(self, message, clientSocket):
            command = message.headers.get("Message")
            sender = message.sender

            if command == protocol.Messages.TEXT:
                recipient = message.headers.get("Recipient")
                text = message.body.decode()  #assuming body is bytes
                #send text to recipient using client manager to find their socket, etc.
            elif command == protocol.Messages.GROUP_TEXT:
                groupID = message.headers.get("Recipient")  #using recipient field to specify groupID for group messages
                text = message.body.decode()
                #send text to all members of the group using group manager to find members and client manager to find their sockets, etc.

            ### ADD MEDIA HANDLING LOGIC HERE, WILL USE UDP FOR MEDIA TRANSFER, THIS IS JUST A PLACEHOLDER FOR NOW

    def handleError(self, message, clientSocket):
            errorCode = message.headers.get("ErrorCode")
            errorMessage = message.body.decode()  #assuming body is bytes
            print(f"Error from client {message.sender}: {errorCode} - {errorMessage}")