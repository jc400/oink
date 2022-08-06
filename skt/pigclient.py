#pig client
"""
This handles sending a message. 

"""

import socket
import selectors
import traceback

from skt import pigclientlibrary


VERBOSE = False

#just returns dict of header info, plus sub-dict with action/value.
def create_request(action, value):

    if action == "message":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, value=value),
        )
    #leaving this here for expansion. Shouldnt be used.   
    else:
        return dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=bytes(action + value, encoding="utf-8"),
        )


#sets up client socket, puts in selector queue
def start_connection(addr, request, sel):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    
    #create SockData object, register with selector. 
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sockdata = pigclientlibrary.SockData(sel, sock, addr, request)
    sel.register(sock, events, data=sockdata)



def sendMessage(addr, message):

    sel = selectors.DefaultSelector()

    request = create_request("message", message)
    start_connection(addr, request, sel)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                sockdata = key.data
                try:
                    sockdata.process_events(mask)
                except Exception:
                    if VERBOSE:
                        print(
                            f"Main: Error: Exception for {sockdata.addr}:\n"
                            f"{traceback.format_exc()}"
                        )
                    sockdata.close()
                    
            # Check for a socket being monitored to continue.
            #whole script exits once single message is sent & acked.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()
        
