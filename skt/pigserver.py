#pig server
"""
listen() method is going to be target of a thread, so it will 
loop constantly in background listening for incoming messages.

We're feeding it a queue object reference (created in model.py) 
which then gets fed down into the sockdata object. So deep down 
in there, in process_request(), is a line to put the parsed message 
into the queue.

Ideally, this means that after starting pigserver, we just...don't 
have to touch it anymore. It chugs along in background, and we can 
just pull whatever we need out of the queue.

However if we do need to stop it (eg to change the IP/port we listen on),
it checks its self.running attribute. We can change that to False from
Model, and then send it a message so it re-evaluates that attribute 
and closes.
"""

import socket
import selectors
import traceback

from skt import pigserverlibrary


class PigServer:

    def __init__(self):
        self.VERBOSE = False
        self.running = False

    def accept_wrapper(self, sock, queue, sel):
        conn, addr = sock.accept()  # Should be ready to read
        conn.setblocking(False)
        sockdata = pigserverlibrary.SockData(sel, conn, addr, queue)
        sel.register(conn, selectors.EVENT_READ, data=sockdata)

    def listen(self, address, queue):
        
        #create selector as local var, so it deletes once thread ends
        sel = selectors.DefaultSelector()
        
        #this is the server socket
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(address)
        lsock.listen()
        print(f"Listening on {address}")
        lsock.setblocking(False)
        
        #register server socket into selector obj
        sel.register(lsock, selectors.EVENT_READ, data=None)

        try:
            #loop checks object's running attribute, this is how we can comm??
            while self.running: #True
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj, queue, sel)
                    else:
                        sockdata = key.data
                        try:
                            sockdata.process_events(mask)
                        except Exception:
                            if self.VERBOSE:
                                print(
                                    f"Main: Error: Exception for {sockdata.addr}:\n"
                                    f"{traceback.format_exc()}"
                                )
                            sockdata.close()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            print('exiting server')
            sel.close()
