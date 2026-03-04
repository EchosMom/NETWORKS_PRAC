"""handles connections"""
import socket
import threading
import protocol     #protocol module

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

    while True:     #server always-on
        clientSocket, clientAddress = serverSocket.accept()
        print("New connection from {}:{}".format(clientAddress[0], clientAddress[1]))

        clientSockets.append(clientSocket)

        thread =threading.Thread(target=handle_client, args=(clientSocket,))
        thread.daemon = True        #thread closes when main program exits.
        thread.start()

if __name__ == "__main__":
    start_server()