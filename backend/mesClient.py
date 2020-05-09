import socket

################################################################################################################################################################################
# *this following is some specifications about the protocol used to communicate to the server*
# *do not expect these to stay the same*

### packet structure
    #the following structure must be followed by both send and the recv

## packets are sent with 2 headers

# header 1 [len = 15] contains the length of the 2 other headers combined
    #this header is used to determain how much we need to recv

# header 2 [len = 20] is the name of the sender
    # i will not be dealing with this header but leave balazs to deal with it as he likes

### connections
# when connecting to the server the first message is a name with 20 padding

################################################################################################################################################################################


def send(session, message):

    try:
        name, socc = session
        #the userneam header is 20 for now
        message = f"{name:<20}{message}"
        header = len(message)
    except:
        return -1

    try:
        socc.send(f"{header:<20}{message}".encode("utf-8"))
    except:
        return -2   



def connect(name, ip, port):
    #try:
        socc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socc.connect((ip, port))
        print("sending login")
        send(socc, name)
        print("sent login")
        return (name, socc)
    #except:
        return 0



# we dont need 2 headers bc balazs can deal with the username
def listen(session):
    name, socc = session
    
    while True:
        #try recv the header of the message
        try:
            message_header = socc.recv(20)
        except:
            return -1

        
        if len(message_header) > 1:
            #try:
            message_len = int(message_header.decode("utf-8").strip())
            return socc.recv(message_len)
            #except: 
            #    return -2
    
