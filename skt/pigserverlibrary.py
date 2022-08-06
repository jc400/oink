import sys
import selectors
import json
import io
import struct

request_search = {
    "morpheus": "Follow the white rabbit. \U0001f430",
    "ring": "In the caves beneath the Misty Mountains. \U0001f48d",
    "\U0001f436": "\U0001f43e Playing ball! \U0001f3d0",
}

"""
Message uses multiple layers of methods to accomplish stuff. Like chains
of function calls.

Also remember that this object is disposable. Hnadles single incoming 
message, creates appropriate response, sends, then destroys itself.

NOTES that all of this stuff can happens over multiple steps / calls. Maybe only 1 byte
comes at a time, and it takes multiple calls from server loop to accomplish it. But 
doesn't matter, because we're checking state along the way, and we're saving state once 
something is ready, and we're using try/catch to avoid IO pitfalls.

Looks like most of the effort here is converting to and from low-level bytes formats,
that can be sent over netwrok. Hence json, struct, io, all the headers, and so on.

And also dealing with the unpredictability and blocking issue.




FLOWCHART:

---------------SERVER STUFF------------------
lsock gets incoming connection, returned out of selector

calls accept_wrapper() to setup client conversation, create message object 
    which is held in data, sets mask to READ ONLY adds client socket to selector
    
when client is ready to read, server loop calls message.process_events()


-------------INSIDE MESSAGE (READ FIRST)---------------
process_events() calls read first, to handle incoming request

read() calls _read() first, to call socket.recv() and put data in buffer

then sequentially processes protoheader, json header, and process_request() 

process_request() decodes json info, saves it to self.request(), then sets
    this message's selector object to WRITE ONLY--we wait until can write response.


--------------INSIDE MESSAGE (WRITE BACK)------------------
now server loop calls process_events() once socket is ready, which calls write()

write() checks queue for response. if not, _create_X_response(), then feeds that into 
    create_message() to format the headers, then saves that into _send_buffer and sets
    the response flag
    
next time around, write() sees that response flag, and calls _write(), which uses 
    socket.send() to send everything in the buffer. Once finished, it close() everything 
    
    






"""

VERBOSE = False

class SockData:

    #This creates all the state stored in message object
    def __init__(self, selector, sock, addr, queue):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False

        self.queue = queue



    #------------INTERNAL FUNCTIONALITY-----------------#

    #changes what events selector listens for
    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.selector.modify(self.sock, events, data=self)


    #reads info from recv(), places into _recv_buffer 
    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:   #only runs if no exception raised
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")


    #sends from _send_buffer via sock.send(). Calls self.close() once all sent.
    def _write(self):
        if self._send_buffer:
            if VERBOSE: 
                print(f"Sending {self._send_buffer!r} to {self.addr}")
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()



    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj


    #creates both headers
    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):  # * means keyword only arguments after it.
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message


    #creates conditional response based on action/value. creates response dict.
    def _create_response_json_content(self):
    
        #self.request is a json object. This finds value for 'action' key
        action = self.request.get("action")
        
        if action == "search":
            query = self.request.get("value")
            answer = request_search.get(query) or f"No match for '{query}'."
            content = {"result": answer}
        elif action == "message":
            content = {"result": "ACKNOWLEDGED AND RECEIVED"}
        else:
            content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response


    #simpler binary response, just echoes binary that was sent
    def _create_response_binary_content(self):
        response = {
            "content_bytes": b"First 10 bytes of request: "
            + self.request[:10],
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        return response






    #-----------API/PUBLIC CALLS---------------------#

    #ALWAYS THE ENTRY POINT!! calls read() or write() depending on selector events
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()


    #STAGE ONE. Sequentially calls low-level stuff to handle the headers,
    #and to decode and process the message. Once finished, changes selector to WRITE.
    def read(self):
    
        #this calls socket.read() & puts data into buffer
        self._read()

        #1st check if we've processed protoheader
        if self._jsonheader_len is None:
            self.process_protoheader()

        #then check if we've processed jsonheader
        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        #once we have message info, actually handle message itself.
        if self.jsonheader:
            if self.request is None:
                self.process_request()


    #STAGE TWO. Once we have request, this calls functions to create appropriate response,
    #then formats response w headers, puts in out buffer, and send(). Once finished, close(). 
    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()

        self._write()


    #cleanup--unregister from selector/close socket/delete reference
    def close(self):
        if VERBOSE:
            print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            if VERBOSE:
                print(
                    f"Error: selector.unregister() exception for "
                    f"{self.addr}: {e!r}"
                )

        try:
            self.sock.close()
        except OSError as e:
            if VERBOSE:
                print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None




    #pull out protoheader from recv buffer. This should be at very top of recv buffer
    #BECAUSE we fully processed previous message according to its length.
    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]


    #pulls json header using length. Checks for required values.
    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header '{reqhdr}'.")


    #pulls incoming message using length from json. Decodes & saves.
    def process_request(self):
    
        #check that we've received enough bytes
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
            
        #pull in data, remove from buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        
        #process based on content-type
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            if VERBOSE:
                print(f"Received request {self.request!r} from {self.addr}")
            
            #adding if statement to print message 
            if self.request.get("action") == "message":
                if VERBOSE:
                    print("New message: ", self.request.get("value"))
                self.queue.put(self.request.get("value"))
            
        else:
            # Binary or unknown content-type
            self.request = data
            if VERBOSE:
                print(
                    f"Received {self.jsonheader['content-type']} "
                    f"request from {self.addr}"
                )
            
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")


    #calls _create_response() --> create_message() then puts in _send_buffer()
    def create_response(self):
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            # Binary or unknown content-type
            response = self._create_response_binary_content()
            
        #both create_response() funcitons return a dict. We feed 
        #dict into create_message() 
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message