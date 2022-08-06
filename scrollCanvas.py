#scrollCanvas class

import tkinter
from functools import partial

class ScrollCanvas(tkinter.Canvas):
    """
    Canvas subclass that just sets up a scroll area. Our scroll callback (tied to root,
    in init) calls the yview_scroll() method of this class to scroll.
    """
    def __init__(self, parent, **kwargs):
        tkinter.Canvas.__init__(self, parent, **kwargs)
        self.scroll_y = tkinter.Scrollbar(self, orient="vertical", command=self.yview)

        
    def finish(self):
        # make sure everything is displayed before configuring the scrollregion
        self.update_idletasks()

        #set scrollregion
        self.configure(scrollregion=self.bbox('all'), 
                       yscrollcommand=self.scroll_y.set)
                         
        #pack canvas
        self.pack(fill='both', expand=True, side='top') 
        
        
class PigCanvas(ScrollCanvas):
    """
    This extends scrollCanvas. We're just holding some data in the object, 
    and adding a callback function to slide messages when the window is resized.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        self.current_Y = 0

        def do_binding():
            self.bind("<Configure>", self.on_resize)
        self.after(1000, do_binding)  

    def on_resize(self, event):
        #I'm shocked this works. We just move all the 'me' items according to event width.
        if event.width != self.width:
            self.moveto('me', x=event.width-300)
            self.width = event.width 
