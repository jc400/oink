#model.py
"""
This is the mid-layer of the application. It encapsulates all of 
the lower level socket stuff, and provides a clean interface for the 
GUI layer (oink.py) to use.

It also stores data for the application while it's running, including
config/state data (like nickname, IP, and so on), and also the conversation 
data.
"""

import threading
import queue
import time
from functools import partial
import socket

import config
from skt import pigclient
from skt import pigserver 
from skt import pigserver



class Model:

    def __init__(self):
    
        if config.USE_LOCALHOST:
            self.ADDRESS = ('127.0.0.1', config.PORT)
        else:
            self.ADDRESS = (self.getIP(), config.PORT)
        self.NICKNAME = self.setOwnNickname()
        self.SCANKEY = config.SCANKEY
        self.REPLKEY = config.REPLKEY
        
        self.contacts = {self.addressToString(self.ADDRESS):{"address":self.ADDRESS, "nickname":"Self"}}
        self.messages = {self.addressToString(self.ADDRESS):[]}
        self.ordered = list(self.contacts.keys())
        
        #for testing
        if False:
            self.fillTestData()
            self.ADDRESS = (self.getLoopbackIP(), config.PORT)
            self.ordered = list(self.contacts.keys())
        
        #for server 
        self.serverObject = pigserver.PigServer()
        self.inQueue = queue.SimpleQueue()
        self.serverThread = None
        self.startServer()
        
        self.updated = False
        
        
      

    #-------------Control the server ----------------#
      
    def setOwnAddress(self, address):
        """Update the IP/Port we listen for messages on"""
        print("setting address to: ", address)
        self.stopServer()
        time.sleep(1)
        
        #save this so we can reference old conversations
        old = self.addressToString(self.ADDRESS)
        
        #check for keyword args
        if address == 'local':
            address = '127.0.0.1;' + str(config.PORT)
        elif address == 'network':
            address = self.getIP() + ';' + str(config.PORT)
        elif address == 'reset':
            address = config.IP + ';' + str(config.PORT)
            
        #set address var
        self.ADDRESS = self.stringToAddress(address)
        
        #update self contact
        self.contacts.pop(old)
        self.contacts[address] = {"address":self.stringToAddress(address), "nickname":"Self"}
        
        #move conversation over
        self.messages[address] = self.messages.pop(old)
        
        self.startServer()

    def startServer(self):
        self.serverObject.running = True
        self.serverThread = threading.Thread(
            target=self.serverObject.listen,   
            args=(self.ADDRESS, self.inQueue),
            name='pigserverThread',
            daemon=True,
        )
        self.serverThread.start() 
        
    def stopServer(self):
        #this controls while loop
        self.serverObject.running = False
        
        #while loop has blocking call, needs to receive something to reval condition
        #we send msg to ourself, to trigger reevaluation of running var.
        self.sendMessage(self.addressToString(self.ADDRESS), 'Stop server')
        self.checkInQueue()
        
    

    #---------------Message / conversations---------------#
    
    def checkInQueue(self):
        #this lives on tk after() loop in GUI, just checks for updates in queue
        newMsgs = self.inQueue.qsize()
        
        for i in range(newMsgs):
            try:
                msg = self.inQueue.get(block=False)
            except self.inQueue.Empty:
                print('Queue empty, couldnt get')
            else:
                if msg['text'] == self.SCANKEY or msg['text'] == self.REPLKEY:
                    self.receiveScan(msg)
                else:
                    self.receiveMessage(msg)
                
    def sendMessage(self, fromkey, text):
    
        self.updated = True
    
        #create message dict
        m = {'to':self.contacts[fromkey]['address'], 
             'from':self.ADDRESS, 
             'timestamp': time.time(),
             'text':text,
            }
            
        #add to our side of conversation
        self.messages[fromkey].append(m) 
        
        #now we have to reorder orderd list 
        try:
            self.ordered.remove(fromkey)
        except ValueError:
            print('got error')
            pass 
        self.ordered.insert(0, fromkey)
    
        #create new thread to call lower-level
        temp = threading.Thread(
            target=pigclient.sendMessage,
            args=(self.contacts[fromkey]['address'], m),
        )
        temp.start()
   
    def receiveMessage(self, msg):
        fromkey = self.addressToString(msg['from'])
        
        #create new contact if not have already
        if fromkey not in self.contacts:
            print('adding contact from non-scan message')
            self.addContact(msg)
            
        #append message
        self.messages[fromkey].append(msg)
        
        #now we have to reorder orderd list, for correct sorting
        self.ordered.remove(fromkey)
        self.ordered.insert(0, fromkey)
            
        #set updated flag to be read by GUI
        self.updated = True
   
   
   
    #------------------Scanning and sync--------------#
    """Client periodically sends out scan to the entire subnet. Other clients 
    receive scan message, add to contacts if new, and send reply. We 
    reply to ALL scans.
    
    Replies also add to contacts if new, but do NOT get reply back. No loop.
    
    Regular messages don't have either key, so we just receiveMessage(). This 
    will still add contact if new, just in case, but skips any reply logic.
    """
   
   
    def scan(self, rnge=None):
        """Accepts range of hosts to scan as tuple/list. Only works for local /24 networks"""
        r1=1
        r2=255
        if rnge:
            r1=rnge[0]
            r2=rnge[1]
        
        #split IP address (from our own IP) into components
        n = self.addressToString(self.ADDRESS).split(';')[0].split('.')
        network = n[0] + '.' + n[1] + '.' + n[2] + '.'
        
        #send scan message to every other host in range
        for host in range(r1, r2):
            dest = tuple([network+str(host), self.ADDRESS[1]])
            m = {'to':dest, 
                 'from':self.ADDRESS, 
                 'timestamp': time.time(),
                 'text':self.SCANKEY,
                 'nickname':self.NICKNAME,
                }
            
            threading.Thread(
                target=pigclient.sendMessage,
                args=(dest, m),
            ).start()
   
    def reply(self, trgt):
    
        if type(trgt) == str:
            trgt = self.stringToAddress(trgt)
    
        m = {'to':trgt, 
             'from':self.ADDRESS, 
             'timestamp': time.time(),
             'text':self.REPLKEY,
             'nickname':self.NICKNAME,
            }
        threading.Thread(
            target=pigclient.sendMessage,
            args=(trgt, m),
        ).start()
   
    def receiveScan(self, msg): 
        fromkey = self.addressToString(msg['from'])
        
        #add contact if new
        if fromkey not in self.contacts:
            print('adding contact from scan message')
            self.addContact(msg)
        
        #we're obligated to reply to scans (but NOT replies)
        if msg['text'] == self.SCANKEY:
            self.reply(fromkey)
   
   
   
   
    #----------Utility functions ------------#
   
    def addressToString(self, addr):
        return addr[0] + ';' + str(addr[1])
       
    def stringToAddress(self, string):
        a = string.split(';')
        b = [a[0], int(a[1])]
        return tuple(b)
    
    def getIP(self):
        #https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/25850698
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
    
    def getLoopbackIP(self):
        random = int(time.time()) % 250
        IP = '127.0.0.' + str(random)
        print('Setting IP to: ', IP)
        return IP
    
    def fillTestData(self):
        #for testing
        a1 = ('127.0.0.5', 49000)
        ua1 = self.addressToString(a1)
        a2 = ('127.0.0.6', 49000)
        ua2 = self.addressToString(a2)
        
        self.contacts[ua1] = {'address':a1, 'nickname':'Alice'}
        self.contacts[ua2] = {'address':a2, 'nickname':'Bob'}
        self.messages[ua1] = [
            {'text':"Hello user, my name is alice and I'm reaaaaaaaaaaaaaal bad", 'from':a1},
            {'text':"oh hello alice how are you doing today my name is user what are you into anyways do you like cars wanna see my car what if we go on a date how about that huh? Want to?", 'from':self.ADDRESS},
            ]
       
        self.messages[ua2] = [
            {'text':"Hello user, my name is bob", 'from':a2},
            {'text':"oh hello bob", 'from':self.ADDRESS},
            ]

        self.contacts['hi'] = {'address':a2, 'nickname':'Eve'}
        self.contacts['ok'] = {'address':a2, 'nickname':'Mal'}
        self.contacts['why'] = {'address':a2, 'nickname':'Aaron'}
        self.contacts['me'] = {'address':a2, 'nickname':'Sue'}

    def setOwnNickname(self):
        """If nickname configured, use it. Else choose random"""
        if config.NICKNAME:
            print('adding nick from config:', config.NICKNAME)
            return config.NICKNAME 
        else:
            nicknames = ['piggy', 'oinker', 'gus', 'snorty', 'hogg', 'mudroe', 'pork chop', 
                         'julianne', 'hamlet', 'truffle', 'babe']
            random = nicknames[int(time.time()) % len(nicknames)]
            print('randomly choosing nickname: ', random)
            return random

    def addContact(self, msg):
        #get data
        fromkey = self.addressToString(msg['from'])
        address = self.stringToAddress(fromkey)     #why do I have to do this?
        try:
            nickname = msg['nickname']
            print('adding nickname from msg ', nickname)
        except KeyError:
            print('adding nickname anonymous')
            nickname = 'anonymous'
        
        #set up
        print('adding contact: ', fromkey)
        self.contacts[fromkey] = {'address': address, 'nickname':nickname}
        self.messages[fromkey] = []
        self.ordered.insert(0, fromkey)
        
        self.updated = True
        
        

if __name__ == "__main__":
    print("I am main! reference 'wp'")
    wp = Model()
    