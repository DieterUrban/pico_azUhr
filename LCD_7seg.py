"""
graphic impl. of 7-seg pattern

"""
#%%


# create 00:00 object for e.g. hour:min display
class HM():
    def __init__(self, pos_x, pos_y, color=0, draw_fct=None):
        self.hh = DIGITS(2, pos_x, pos_y, color, draw_fct, right_separator=':')
        pos_x2 = self.hh.x_next
        self.mm = DIGITS(2, pos_x2, pos_y, color, draw_fct, right_separator='')
        self.x_next = self.mm.x_next
        self.y_next = pos_y


    def set(self, value):    # value is already '01:22' type string
        hh,mm = str(value).split(':')
        self.hh.set(hh)
        self.mm.set(mm)

    def clear(self):
        self.hh.clear()
        self.mm.clear()


# multiple 7-seg objects to form n_digits size object
class DIGITS():
    def __init__(self, n_digits,       # number digits
                 pos_x, pos_y,         # bottom left x,y position as for text
                 color = 0x255,        # active color. assuming 0 (black) for clear
                 draw_fct=None,        #  draw_fct(p1=(x,y), p2=(x,y), color):
                 left_aligned=False,   # fill value characters starting from left digit
                 fill_zeros=True,      # fill missing valule characters with 0 (otherwise black/off)
                 right_separator = '', # can be '.' or ':' as alternative
                 ):
        
        self.x_next = 0            # x position of next digits object with same spacing
        self.y_next = 0            # y position of next line for digits objects
        self.sseg = []             # list of digits object
        self.value = ''            # string representing value , e.g. '01' or '35'
        self.right_separator = right_separator   # '.' or ':' to show '01:' or '35.'
        
        x=pos_x
        y=pos_y
        for d in range(n_digits):
            digit = SSEG(x,y,color,draw_fct)
            self.sseg += [digit]
            x = digit.x_next
            # y = digit.y_next same line
        
        self.x_next = x
        self.y_next = y

    
    def set(self, value):
        self.value = str(value)
        if len(self.value) < len(self.sseg):
            n_gap = len(self.sseg) - len(self.value)
            fill = '0' if self.fill_zeros else 'x'
            if self.left_aligned:
                self.value += fill*n_gap
            else:
                self.value = fill*n_gap + self.value
        self.draw()

        
    # redwraw    
    def draw(self, clear=False):
        i_max = len(self.sseg)-1
        pt = ''
        for i,ss in enumerate(self.sseg):
            if i < len(self.value):
                d = self.value[i]
                if i == i_max:
                    pt=self.right_separator
                ss.set(d,pt=pt)
            else:
                ss.clear()
        


    def clear(self):
        self.draw(clear=True)
        
        
# a single digit 7-seg object 
class SSEG():
    
    # position of the 7 segments as relative coord.  top left = 0,0  , for size 16x18 font.  definition includes separation withing size
    # Segments = t, m , b  (horizontal top...bot), tl, tr and bl,br for top-left ... bottom-right vertical segments
    @classmethod
    def setSize(cls, x_digit_separation=4, x_digit_size=10, y_digit_separation=4, y_digit_size=14):

        SSEG.XSEP =  x_digit_separation # separation in x
        SSEG.SX = x_digit_size          # digit size x, left aligned
        SSEG.XSIZE = SSEG.SX+SSEG.XSEP  # size incl separation
        SSEG.PSX = SSEG.XSIZE-1         # decimal point position
        

        SSEG.YSEP = y_digit_separation  # separation in y between digit lines
        SSEG.SY = y_digit_size          # digit size y  (top aligned)
        SSEG.YSIZE = SSEG.SY+SSEG.YSEP  # size incl. separation
        SSEG.SY2 = round(SSEG.SY/2)     # digit size y/2, midd position from top
        SSEG.PSY = SSEG.SY              # decimal point position from top
        SSEG.PYD = round(SSEG.SY/8)     # : position, distance from top / bot
    
        SSEG.segments = {
                    't':[[0,0],[SSEG.SX,0]],
                    'm':[[0,SSEG.SY2],[SSEG.SX,SSEG.SY2]],
                    'b':[[0,SSEG.SY],[SSEG.SX,SSEG.SY]],
                    'tl':[[0,0],[0,SSEG.SY2]],
                    'bl':[[0,SSEG.SY2],[0,SSEG.SY]],
                    'tr':[[SSEG.SX,0],[SSEG.SX,SSEG.SY2]],
                    'br':[[SSEG.SX,SSEG.SY2],[SSEG.SX,SSEG.SY]],
                    '.':[[SSEG.PSX,SSEG.PSY],[SSEG.PSX,SSEG.PSY]],
                    ':t':[[SSEG.PSX,SSEG.PYD],[SSEG.PSX,SSEG.PYD]],
                    ':b':[[SSEG.PSX,SSEG.PSY-SSEG.PYD],[SSEG.PSX,SSEG.PSY-SSEG.PYD]]
                    }

        # mapping of digits (or alpha) to involved segments 
        SSEG.digit2segment = {
                         '1':['tr','br'],
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
                         ':':[':t',':b'],
                         'x':[]
                          }
        
    def __init__(self, 
                 pos_x, pos_y,  # bottom left x,y position as for text
                 color = 0,     #  0 for black (clear)
                 draw_fct=None):     #  draw_fct(p1=(x,y), p2=(x,y), color) 
        
        self.pos_x = pos_x
        self.pos_y = pos_y - SSEG.SY
        self.x_next = self.pos_x + SSEG.XSIZE   # positions for next digit
        self.y_next = self.pos_y + SSEG.YSIZE
        self.size = None
        self.value = 'x'    # 'x' is off
        self.draw = draw_fct
        self.color = color
        self.color_clear = 0x0000
        self.segments = []   # list of activated SEGMENT ojects
    
    # set segments according new value to show
    def set(self,value,pt=''):
        self.clear()
        if not str(value) in SSEG.digit2segment.keys():
            return
        for s in SSEG.digit2segment[str(value)]:
            self.segments += [s]
            self.draw_segment(s)
        if pt:
            # draw '.' or ':' 
            for s in SSEG.digit2segment[pt]:
                self.draw_segment(s)
            
        
    def draw_segment(self, segment, clear=False):
        color = self.color_clear if clear else self.color
        s = SSEG.segments[segment]
        s1 = s[0]
        s2 = s[1]
        p1 = [s1[0]+self.pos_x, s1[1]+self.pos_y]
        p2 = [s2[0]+self.pos_x, s2[1]+self.pos_y]
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
        
    
    digit1 = SSEG(0,100,color=1, draw_fct=printFct)
    digit2 = SSEG(SSEG.SX,100,color=1, draw_fct=printFct)
    
    digit1.draw_segment('t')
    digit1.clear()

    digit1.set(0)
    digit2.set(1,pt=True)


