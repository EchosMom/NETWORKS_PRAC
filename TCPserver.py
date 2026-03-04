"""handles connections"""
import socket
import threading

serverAddress = "127.0.0.1"  # Localhost
serverPort = 1500

clientSockets = []

def handle_client(clientSocket): #handles the client connection
    while True:
        #code to handle client messages and broadcast to other clients
        #receiving msg
        try:
            msg = clientSocket.recv(1042).decode    #taken from slides
            if not msg:     #client disconnected
                break

            #broadcasting function
            for sock in clientSockets:
                if sock != clientSocket:        #do not send to the sender
                    try:
                        sock.send(msg.encode())
                    except:         #remove dead conns
                        clientSockets.remove(sock)
        except:
            break

        clientSocket.close()
        if clientSocket in clientSockets:
            clientSockets.remove(clientSocket)

def start_server():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((serverAddress, serverPort))
    serverSocket.listen()

    print("Server is listening on {}:{}".format(serverAddress, serverPort))

    while True:
        clientSocket, clientAddress = serverSocket.accept()
        print("New connection from {}:{}".format(clientAddress[0], clientAddress[1]))

        clientSockets.append(clientSocket)

        thread =threading.Thread(target=handle_client, args=(clientSocket,))
        thread.start()