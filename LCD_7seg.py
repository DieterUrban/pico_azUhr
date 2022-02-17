"""
graphic impl. of 7-seg pattern

"""
#%%

class SSEG():

    # position of the 7 segments as relative coord.  top left = 0,0  , for size 16x18 font.  definition includes separation withing size
    # Segments = t, m , b  (horizontal top...bot), tl, tr and bl,br for top-left ... bottom-right vertical segments
    SX = 8-1    # size x, separation 1, left aligned
    PSX = 8     # decimal point position
    SY = 16-2   # size y, separation 2, bottom aligned
    SY2 = 7     # size y/2, midd position from top
    PSY = 16
    
    
    segments = {'t':[[0,0],[SX,0]],
                'm':[[0,SY2],[SX,SY2]],
                'b':[[0,SY],[SX,SY]],
                'tl':[[0,0],[0,SY2]],
                'bl':[[0,SY2],[0,SY]],
                'tr':[[SX,0],[SX,SY2]],
                'br':[[SX,SY2],[SX,SY]],
                '.':[[PSX,PSY],[PSX,PSY]]
                }

    # mapping of digits (or alpha) to involved segments 
    digit2segment = {'1':['tr','br'],
                     '2':['t','b','tr','bl','m'],
                     '3':['t','b','tr','br','m'],
                     '4':['tl','tr','br','m'],
                     '5':['t','b','tl','br','m'],
                     '6':['b','tl','bl','br','m'],
                     '7':['tr','br','t'],
                     '8':['t','b','tl','tr','bl','br','m'],
                     '9':['t','tl','tr','br','m'],
                     '0':['t','b','tl','tr','bl','br'],
                     '-':['m'],
                     '_':['b'],
                     '.':['.'],
                     'off':[]
                         }
    
    def __init__(self, 
                 pos_x, pos_y,  # bottom left x,y position as for text
                 color = 0,     #  0 for black (clear)
                 draw_fct=None):     #  draw_fct(p1=(x,y), p2=(x,y), color) 
        
        self.pos_x = pos_x
        self.pos_y = pos_y - SSEG.SY
        self.pos_x_next = self.pos_x + SSEG.SY
        self.size = None
        self.value = 'off'
        self.draw = draw_fct
        self.color = color
        self.color_clear = 0
        self.segments = []   # list of activated SEGMENT ojects
    
    # set segments according new value to show
    def set(self,value,pt=False):
        self.clear()
        if not str(value) in SSEG.digit2segment.keys():
            return
        for s in SSEG.digit2segment[str(value)]:
            self.segments += [s]
            self.draw_segment(s)
        if pt:
            self.draw_segment('.')
            
        
    def draw_segment(self, segment, clear=False):
        color = self.color_clear if clear else self.color
        s = SSEG.segments[segment]
        p1 = [s[0][0]+self.pos_x, s[1][0],self.pos_y]
        p2 = [s[0][1]+self.pos_x, s[1][1],self.pos_y]
        self.draw(p1, p2, color)
    
    # set all active segments off
    def clear(self): 
        for s in self.segments:
            self.draw_segment(s,clear=True)
        self.segments = []


    def debug_draw(p1, p2, color):
        print("col",color)
        print(p1,p2)
    
        

#%%

if False:
    # import plottext as plt    # use plottext to plot to console
    
    def printFct(p1, p2, color):
        print("col",color)
        print(p1,p2)
        
    
    digit1 = SSEG(0,16,color=1, draw_fct=printFct)
    digit2 = SSEG(SSEG.SX,16,color=1, draw_fct=printFct)
    
    digit1.draw_segment('t')
    digit1.clear()

    digit1.set(0)
    digit2.set(1,pt=True)


