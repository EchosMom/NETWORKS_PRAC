#file taht will handle basic sercurity vulnerablity in terms of filtering user input

MAX_LENG = 1000 #

#basic input sanitization
def sanitize_input(text):
    if not text or len(text)>MAX_LENG:
        return None
    #removes control characters
    sanitized = ''.join(char for char in text if ord(char)>=32 or char =='\n')
    #for terminal output, replace ESC character
    sanitized = sanitized.replace('\x1b', '?')
    return sanitized

def username_is_safe(username):
    if not username or len(username)>30:
        return False
    return all(c.isalnum() or c in '._-' for c in username)

def IP_port_is_safe(ip_port_string):
    try:
        ip, portString = ip_port_string.split(":")
        portNum = int(portString)

        #check ip
        parts = ip.split('.')
        if len(parts) !=4:
            return False
        
        #check port range
        if not (1024<=port<=65535):
            return False
        return True
    except:
        return False