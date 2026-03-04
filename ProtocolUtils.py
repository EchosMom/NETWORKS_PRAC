#this file adds usability to the protocol.py
import protocol

class ProtocolUtils:

    def __init__(self, headers=None, body=b"'"):
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
        return protocol.Protocol.encodeMessage(self.messageType, self.message, self.sender, Recipient=self.recipient, body=self.body,**{k.lower(): v for k, v in self.headers.items() if k not in ["MessageType", "Message", "Sender", "Recipient"]})
        