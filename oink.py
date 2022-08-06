#GUI interface

import model
import config
import scrollCanvas

import tkinter
from tkinter import ttk 
from functools import partial
import os


class Gui:
    
    #-------------Setup functions-----------#
    
    def __init__(self):
    
        self.root = tkinter.Tk()
        self.root.title("Oink")
        
        #Define data and references\
        self.POLLFREQUENCY = 1000   #in ms--1000 = 1 second
        self.SCANFREQUENCY = 5000
        self.DIRPATH = os.path.dirname(__file__)
        self.model = model.Model()  #reference to mid layer
        self.fromkey = self.model.addressToString(self.model.ADDRESS) #current convo we looking at
        self.contactScroll = None 
        self.convoScroll = None
        self.darkmode = config.DARKMODE
            
        #GUI initialization steps
        self.images = {'me':{}, 'th':{}, 'btn':{}}
        self.loadImages()
        (self.setLightColors, self.setDarkColors)[self.darkmode]() #ternary from stackoverflow
        self.initStyles()
        
        #On scroll event, check X coordinate and scroll appropriate GUI section.
        #https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        def _on_mousewheel(event):
            if self.root.winfo_pointerx()-self.root.winfo_rootx() < 330:
                self.contactScroll.yview_scroll(int(-1*(event.delta/120)), "units")
            else:
                self.convoScroll.yview_scroll(int(-1*(event.delta/120)), "units")
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
               
        #create skel frames to hold contacts, conversations
        self.contactSkel = ttk.Frame(self.root, width=330, height=600, style="G.TFrame")
        self.contactSkel.pack_propagate(False)
        self.contactSkel.pack(side='left', fill='y')
        
        self.convoSkel = ttk.Frame(self.root, style="B.TFrame")
        self.convoSkel.pack(side='left', fill='both', expand=True)

        #setup view, start loop
        self.poll()
        self.scanLoop()
        self.ContactsView() 
        self.ConvoView()
        self.root.mainloop()


    def loadImages(self):
        
        def getImg(filename):
            """Helper function"""
            return tkinter.PhotoImage(file=os.path.join(self.DIRPATH, 'images', filename))
        
        self.images['me']['lid'] = getImg('lid_me.png')
        self.images['me']['base'] = getImg('base_me.png')
        self.images['th']['lid'] = getImg('lid_them.png')
        self.images['th']['base'] = getImg('base_them.png')
        self.images['btn']['sttg'] = getImg('hamburger.png')


    def setDarkColors(self):        
        self.gr = "gray17"      #used for bg on left side
        self.bl = "black"       #used for bg on right side
        
        self.dg = "gray10"      #darker than default bg 
        self.lg = "gray30"      #lighter
        
        self.tx = "gray64"      #regular text (eg message previews)
        self.title = "snow"     #conversation names, titles. Whiter.
        self.cv = "gray95"      #test on pig in conversations
        
        #for messages. Convert RGB values into hex
        self.thColor = "#%02x%02x%02x" % (79,79,79)
        self.meColor = "#%02x%02x%02x" % (239, 121, 171)
        
     
    def setLightColors(self):
        self.gr = "gray70"      #used for bg on left side
        self.bl = "gray90"       #used for bg on right side
        
        self.dg = "gray60"      #darker than default bg 
        self.lg = "gray80"      #lighter
        
        self.tx = "gray10"      #regular text
        self.title = "black"     #conversation names, titles. Whiter.
        self.cv = "gray95"      #test on pig in conversations

        #for messages
        self.thColor = "#%02x%02x%02x" % (79,79,79) 
        self.meColor = "#%02x%02x%02x" % (239, 121, 171)

     
    def initStyles(self):
    
        try:
            self.style.destroy()
        except AttributeError:
            pass
    
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        #frames 
        if True:
            #contact side frames
            self.style.configure("G.TFrame", 
                                 background=self.lg,
                                )
            #convo side frames             
            self.style.configure("B.TFrame",
                                 background=self.bl,
                                ) 
            #frame for settings 
            self.style.configure("S.TFrame",
                                 background=self.gr,
                                )
        
        #Contacts side header (gray)
        if True: 
            self.style.configure("G.TButton", 
                                 background=self.lg, 
                                 foreground=self.title,
                                 relief='flat',
                                )
            self.style.map('G.TButton', background=[('active', self.tx)])
            
            self.style.configure("G.TLabel",
                                 justify='center',
                                 foreground=self.title,
                                 background=self.lg,
                                 padding=10,
                                 font=('arial bold', 20)
                                )
        
        #contacts side messages
        if True:
            #for text of message blurb 
            self.style.configure("C1.TLabel",
                                 font=('arial', 13),
                                 justify='left',
                                 background=self.gr,
                                 foreground=self.tx,
                                )
            
            #for nickname of message blurb
            self.style.configure("C2.TLabel",
                                 font=('arial bold', 13),
                                 background=self.gr,
                                 foreground=self.title,
                                )

            #contacts separator
            self.style.configure("C.TSeparator",
                                 background=self.tx,
                                )

        #contacts side messages (if highlighted)
        if True:
            #for text of message blurb 
            self.style.configure("Chighlight1.TLabel",
                                 font=('arial', 13),
                                 justify='left',
                                 background=self.bl,
                                 foreground=self.tx,
                                )
            
            #for convo title (eg the nickname) its bold
            self.style.configure("Chighlight2.TLabel",
                                 font=('arial bold', 13),
                                 background=self.bl,
                                 foreground=self.title,
                                )

        #convo side header (black)
        if True:     
            self.style.configure("B.TLabel", 
                                 justify='center',
                                 foreground=self.title,
                                 background=self.bl,
                                 padding=10,
                                 font=('arial bold', 20)
                                )
        
        #convo footer
        if True:
            self.style.configure("BFooter.TFrame",
                                 background=self.dg,
                                ) 
            
            self.style.configure("BFooter.TButton",
                                 background=self.dg,
                                 foreground=self.tx,
                                 padding=5,
                                 relief='flat',
                                )
            self.style.map('BFooter.TButton', background=[('active', self.gr)])
      
      
    #-------------Views--------------------#
  

    def ContactsView(self):
    
        #setup
        if True:
            try:
                self.contactsFrame.destroy() 
            except AttributeError:
                pass
                
            self.contactsFrame = tkinter.Frame(self.contactSkel, bg='black') 
            self.contactsFrame.pack(fill='both', expand=True)
            
      
        #contacts header
        if True:
            HF = ttk.Frame(self.contactsFrame, style="G.TFrame", height=50)
            HF.pack(side='top', fill='x')
            
            #settings
            settings = ttk.Button(HF, image=self.images['btn']['sttg'], style="G.TButton", width=6) 
            settings.configure(command=self.SettingView)
            settings.pack(side='left')
            
            #label
            ttk.Label(HF, text="Messages", style="G.TLabel").pack(side='top')
 
 
        #contacts scroll area 
        if True:
            #create scrolling canvas, create frame inside canvas
            self.contactScroll = scrollCanvas.ScrollCanvas(self.contactsFrame, highlightthickness=0, bg=self.gr) 
            frame = tkinter.Frame(self.contactScroll, bg=self.gr)

            #callback used by widgets
            def callback(event, fk=None):
                self.fromkey = fk 
                self.ConvoView()
                self.ContactsView()

            #create scrollable group of widgets, inside frame (inside canvas)
            for fromkey in self.model.ordered:
                #get data
                nickname = '\n' + self.model.contacts[fromkey]['nickname']
                try:
                    last = self.model.messages[fromkey][-1]['text']
                except KeyError:
                    last = 'No messages yet :( \n(key)'
                except IndexError:
                    last = "no messages yet :( \n(index)"
                    
                #format text nicely
                frmtText, rows = self.formatMessage(last[:70], lineLength=35)
                if rows == 2:
                    frmtText = frmtText[:frmtText.rfind('\n')] + '...'
                elif rows == 0:
                    frmtText = frmtText + '\n '
                   
                #message frame   
                msgFrame = tkinter.Frame(frame, width=300, height=60, bg=self.gr)
                msgFrame.pack_propagate(False)
                msgFrame.pack(fill='x', ipady=15, ipadx=15)
                
                #bolded name label
                name = ttk.Label(msgFrame, style="C2.TLabel", text=nickname)
                name.bind("<Button-1>", partial(callback, fk=fromkey))
                name.pack(side="top", fill='x', padx=15)
                
                #unbolded message text
                text = ttk.Label(msgFrame, style="C1.TLabel", text=frmtText)
                text.bind("<Button-1>", partial(callback, fk=fromkey))
                text.pack(side="top", fill='x', expand=True, padx=15)
                
                #separator
                ttk.Separator(frame, style="C.TSeparator").pack(fill='x', padx=15)
                
                #check if this is current convo--if yes, highlight
                if fromkey == self.fromkey:
                    msgFrame['bg'] = self.bl 
                    name['style'] = "Chighlight2.TLabel"
                    text['style'] = "Chighlight1.TLabel"
                
            #pack the frame, and create view window within the canvas to show frame
            frame.pack(fill='both')
            self.contactScroll.create_window(0, 0, anchor='nw', window=frame)
            self.contactScroll.finish()


    def ConvoView(self):

        #setup
        if True:
            try:
                self.convoFrame.destroy()
            except AttributeError:
                pass
            
            self.convoFrame = tkinter.Frame(self.convoSkel) 
            self.convoFrame.pack(fill='both', expand=True)
             
            fromkey = self.fromkey
            
        
        #convo header
        if True:
            HF = ttk.Frame(self.convoFrame, style="B.TFrame", height=50)
            HF.pack(side='top', fill='x')
            
            #conversation title (eg nickname)
            ttk.Label(HF, text=self.model.contacts[fromkey]['nickname'], 
                      style="B.TLabel").pack(side='top')

              
        #footer
        if True:
            footerFrame = ttk.Frame(self.convoFrame, style="BFooter.TFrame", height=50)
            footerFrame.pack_propagate(False)
            footerFrame.pack(side='bottom', fill='x')
                
            #send callback
            def setupSend(event=None):
                #get entry
                text = entry.get("1.0", "end-1c")
                entry.delete("1.0", "end-1c")
                
                #send
                self.model.sendMessage(fromkey, text)
                
                #update screen 
                self.ContactsView()
                self.ConvoView()
                
            #send button
            ttk.Button(footerFrame, text="Send", style="BFooter.TButton",
                command=setupSend).pack(side='right', fill='y')
            
            #text entry field
            entry = tkinter.Text(footerFrame, relief='flat',
                font=('arial', 12), bg=self.gr, fg=self.tx)
            entry.bind('<Return>', setupSend)
            entry.pack(side='right', padx=20, pady=10)
            entry.focus_set()
        
        
        #scroll area (pig texts)
        if True:
            #create our scrolling canvas object
            self.convoScroll = scrollCanvas.PigCanvas(self.convoFrame, bg=self.bl, highlightthickness=0)

            #draw each message w handy appendMessage()
            for msg in self.model.messages[fromkey]:
                self.appendMessage(self.convoScroll, msg)
            
            #finish setting up scroll canvas, move view to bottom
            self.convoScroll.finish()
            self.convoScroll.yview_moveto(self.convoScroll.current_Y)
 
 
    def SettingView(self):
        
        self.settingWin = tkinter.Toplevel()
        self.settingWin['bg'] = self.gr
        
        #dark mode button
        frame1 = ttk.Frame(self.settingWin, style="S.TFrame")
        frame1.pack(side='top', fill='both', padx=20, pady=20)
        
        def setDark():
            if self.darkmode:
                self.setLightColors()
                self.darkmode = False
                print('activating light mode')
            else:
                self.setDarkColors()
                self.darkmode = True
                print('activating dark mode')
            self.settingWin.destroy()
            self.initStyles()
            self.ContactsView() 
            self.ConvoView()
                
        ttk.Label(frame1, text="Dark Mode", style="C1.TLabel").pack(side='left')
        ttk.Button(frame1, text="click me", style="G.TButton", command=setDark).pack(side='right', padx=20)
     
     
        #nickname 
        frame2 = ttk.Frame(self.settingWin, style="S.TFrame")
        frame2.pack(side='top', fill='both', padx=20, pady=20)
        
        nicknameVar = tkinter.StringVar()
        nicknameVar.set(self.model.NICKNAME)
  
        ttk.Label(frame2, text="Update nickname", style="C1.TLabel").pack(side='left')
        nicknameEntry = tkinter.Entry(frame2, textvar=nicknameVar)
        nicknameEntry.pack(side='right', padx=20)
        
        def submitNickname(event):
            nickname = nicknameVar.get()
            self.model.NICKNAME = nickname
            print('setting nickname to ', nickname)
            self.settingWin.destroy()
        nicknameEntry.bind("<Return>", submitNickname)    
        
    
    
    #-------------Helper functions-----------#
    
    
    def poll(self):
        """runs in loop, asks model obj to check queue, updates GUI if necessary"""
        self.model.checkInQueue()
        
        #we're lazy, just reload everything to render update. This could be way better.
        if self.model.updated:
            self.ConvoView()
            self.ContactsView()
            self.model.updated = False
            
        self.root.after(self.POLLFREQUENCY, self.poll)


    def scanLoop(self):
        """asks model to scan for other oink clients (by blasting packets)"""
        self.model.scan()
        self.root.after(self.SCANFREQUENCY, self.scanLoop)


    def formatMessage(self, text, lineLength=35):
        chopped = text.split(' ')
        formatted = ''
        templine = ''
        rowcount = 0
        
        for word in chopped:
            if len(word) > lineLength:
                #dump previous line
                if templine != '':
                    formatted += templine + '\n'
                    templine = ''
                
                #get length of long word, break it up over lines
                r = len(word) // lineLength
                for i in range(r):
                    formatted += word[i*lineLength:(i+1)*lineLength] + '\n'
                    rowcount += 1
                    
                #add remainder to templine and carry on
                templine += word[r*lineLength:]
                
            elif (len(word) + len(templine)) > lineLength:
                formatted = formatted + templine + '\n'
                rowcount += 1
                templine = word + ' '
                
            else:
                templine = templine + word + ' '
                
        formatted += templine 
        
        return formatted, rowcount
                
    
    def appendMessage(self, pigCanvas, msg):
        """We're manually calculating pixel where new message should be placed"""
        
        #get far end of window, adjust to canvas (which is offset to right by 330 px
        #create swtch dict to configure canvas items
        w = self.root.winfo_width() - 330  
        swtch = {'me':{'x1':w-300, 
                       'x2':w-5, 
                       'xm':w-275, 
                       'clr':self.meColor,
                       'tag':'me'},
                 'th':{'x1':5, 
                       'x2':300, 
                       'xm':30, 
                       'clr':self.thColor,
                       'tag':'th',}
                }
    
        #set S (sender) key for use in swtch, self.images{}
        if msg['from'] == self.model.ADDRESS:
            S = 'me'
        else:
            S = 'th'
          
        #format message
        formatted, rows = self.formatMessage(msg['text'])
        yspan = rows*18

        #rect to hold text
        self.convoScroll.create_rectangle((swtch[S]['x1'], pigCanvas.current_Y,
                                 swtch[S]['x2'], pigCanvas.current_Y+yspan),
                                fill=swtch[S]['clr'],
                                outline='', 
                                tag=swtch[S]['tag'],
                               )
                               
        #lid 
        self.convoScroll.create_image((swtch[S]['x1'], pigCanvas.current_Y+2), 
                            anchor='sw',
                            image=self.images[S]['lid'],
                            tag=swtch[S]['tag'],
                           )
                           
        #base
        self.convoScroll.create_image((swtch[S]['x1']-5, pigCanvas.current_Y+yspan),
                            anchor='nw',
                            image=self.images[S]['base'],
                            tag=swtch[S]['tag'],
                           )
        
        #text message itself
        self.convoScroll.create_text((swtch[S]['xm'], pigCanvas.current_Y),
                           text=formatted,
                           anchor='nw',
                           font=('arial', 12),
                           fill=self.cv,
                           tag=swtch[S]['tag'],
                          )
            
        #yspan for rows, 18 for last one, padding
        pigCanvas.current_Y += yspan + 18 + 35   





test1 = Gui() 

