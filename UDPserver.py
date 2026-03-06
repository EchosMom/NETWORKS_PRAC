# UDP will only handle the binary media messages

import socket
import threading
import protocol
from ProtocolUtils import ProtocolUtils


class UDPServer:
    def __init__(self, host="127.0.0.1", port=1501):        #udp port from protocol
        self.host = host    
        self.port = port
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    """START SERVER"""
    def start(self):
        self.serverSocket.bind((self.host, self.port))
        print(f"UDP Server listening on {self.host}:{self.port}")

        while True:
            data, addr = self.serverSocket.recvfrom(protocol.Protocol.MAX_MESSAGE_BODY_SIZE)        #diff between tcp/ udp = recvfrom(data, address)

            thread = threading.Thread(
                target=self.handle_packet,
                args=(data, addr),
                daemon=True
            )
            thread.start()

    """process the UDP packet"""
    def handle_packet(self, data, addr):
        try:
            message = ProtocolUtils.decode(data)    #for consistency in formatting between TCP/UDP

            sender = message.sender
            msg_type = message.messageType
            command = message.message

            print(f"UDP packet from {addr} | Sender: {sender}")     #fror testing reasons

            #register peer location
            if sender and sender not in self.peers:
                self.peers[sender] = addr

            #handle binary media 
            if message.is_media():
                self.handle_media(message, addr)

            elif message.is_group_media():
                self.handle_group_media(message)

            else:
                print("Unknown UDP message type")

        except Exception as e:
            print(f"UDP packet error: {e}")

    """send media to peer"""
    #tracks peers usrname and ip (self, addr)
    def handle_media(self, message, addr):
        recipient = message.recipient

        if recipient not in self.peers:
            print(f"Recipient {recipient} not known")
            return

        recipient_addr = self.peers[recipient]

        print(f"Forwarding media from {message.sender} to {recipient}")

        self.serverSocket.sendto(message.encode(), recipient_addr)

    """send media to group chat"""
    def handle_group_media(self, message):
        group_id = message.recipient

        #get members from group manager
        group_members = []  

        for member in group_members:
            if member in self.peers:
                self.serverSocket.sendto(message.encode(), self.peers[member])

if __name__ == "__main__":
    udp_server = UDPServer(port=1501)
    udp_server.start()