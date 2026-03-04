"""builds messages"""
from wsgiref import headers


class MessageType:
    COMMAND = "COMMAND"
    CONTROL = "CONTROL"
    DATA = "DATA"

class Messages:
        #command messages
        LOGIN = "LOGIN"
        LOGOUT = "LOGOUT"
        JOIN = "JOIN"
        LEAVE = "LEAVE"
        CREATE_GROUP = "CREATE_GROUP"
        CHAT_REQUEST = "CHAT_REQUEST"
        CHAT_ACCEPT = "CHAT_ACCEPT"
        CHAT_REJECT = "CHAT_REJECT"

        #control messages
        ACK = "ACK"
        ERROR = "ERROR"
        CHAT_INFO = "CHAT_INFO"

        #data messages
        TEXT = "TEXT"
        GROUP_TEXT = "GROUP_TEXT"
        MEDIA = "MEDIA"
        GROUP_MEDIA = "GROUP_MEDIA"

class ErrorCodes:
      INVALID_COMMAND = 400
      NOT_FOUND = 404
      VALID = 200
      SERVER_ERROR = 500

class Protocol:
      TCP_PORT = 1500   
      #UDP_PORT 
      MAX_HEADER_SIZE = 4096 #wont allow message header longer than 4kb
      MAX_MESSAGE_BODY_SIZE = 65536 #wont allow message longer than 64kb taken from common lengths reccomended in early internet
      #UDP packet size

      @staticmethod #create message from specified protocol
      def encodeMessage(type, message, sender, **kwargs):
         headers = { f"MessageType: {type}", f"Message: {message}", f"Sender: {sender}" }

         #add any additional headers from kwargs
         for key, value in kwargs.items():
            if key != 'body' : #body would be a text massage or binary media being sent
             headers.add(f"{key}: {value}")
             
         headers.add("") #add empty line to indicate end of headers
         headerString = "\n".join(headers)

         #if data message, include body
         body = kwargs.get('body', "")
         if body:
             return headerString.encode() + body.encode() if isinstance(body, str) else headerString.encode() + body #combine headers and body into one byte string
             return headerString.encode() #just return headers as byte string if no body
         
      @staticmethod #devide message into headers and body
      def decodeMessage(data):
        try:
            parts = data.split(b"\n\n", 1) #split headers and body at first double newline
            headerPart = parts[0].decode("utf-8", errors = "ignore") #decode headers from bytes to string
            body = parts[1] if len(parts) > 1 else b"" #get body as bytes if it exists

            headers = {}
            for line in headerPart.split("\n"): #split headers into lines and parse key-value pairs
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key.strip()] = value.strip()
            return headers, body
        except Exception as e:
            print(f"Error decoding message: {e}")
            return {}, b""