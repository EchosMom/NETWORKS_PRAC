"""this class is made for the UDP transfer based on P2P connection"""
"""p2p handshake is made in tcp server"""
""" we only use udp for p2p connection and transfer of binary media"""

import socket
import threading

class UDPClient:

    def __init__(self, port=1501):          #claim port 1501
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", port))     #ip tells to listen from all IPs on your device

    def start_listener(self):
        thread = threading.Thread(target=self.listen)
        thread.daemon = True
        thread.start()

    def listen(self):
        while True:
            data, addr = self.socket.recvfrom(65535)
            print(f"Received media from {addr}")

    def send_media(self, ip, port, data):
        self.socket.sendto(data, (ip, port))