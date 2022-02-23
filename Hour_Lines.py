#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 23 13:32:16 2022

functions to use LCD_7seg

@author: urban
"""

#####################################################
# Generate display Output format
"""
Tag WTag  AZ     Pause  +/-
0   Fr    00:00  00:00  00:00
-1  Do    
-2  Mi
-3  Di
-4  Mo
Woche     00:00  00:00  00:00
W-1       00:00  00:00  00:00
Sollzeit: 35h
"""

class Hour_Lines():
    """
    Provides:
        Anzeige von 5 Zeilen jeweils: AZ, +/- und Pause
    """
    header = ['AZ','+/-', 'Pause']                # header line text, not used yet
    intro = [' 0  ','-1  ','-2  ','-3  ','-4  ']  # default start text for lines
    days = ['Mo','Di','Mi','Do','Fr','Sa','So']             # 2nd position start text for lines
    
    def __init__(self, x0, y0, dx, dy, color, lines=5, intro=None):  # x0 = 1st digit start, dx = separation between hh:mm
        self.hhmm = []  # will get 5 hh:mm display objects
        self.actual = 0  # pointer to actual day in days, 0 is monday
        self.setPlan(39./5)
        intro = intro or Hour_Lines.intro.copy()
        
        for i in range(lines):
            line_hhmm = Hour_Line(x0, y0, color, dx, intro[i])
            self.hhmm += [line_hhmm]
            y0  += dy  # next line y value
        self.y_next = y0
        self.values = self.hhmm[0].values
     
    # set defaults as worktime plan ...
    def setPlan(self, hourPlan):
        self.hourPlan = hourPlan
    
    # update todays values and print/show-update first line
    def update(self, az,balance,breaktime):
        # print("update")
        self.values = [az, balance, breaktime]
        wday_string = Hour_Lines.days[self.actual]
        # print(self.hhmm)
        self.hhmm[0].set(self.values, wday_string)
        
    # show first or all lines
    def show(self, all=False):
        # print("show all=", all)
        #if type(self.hhmm[0]) == list:
        #    print("show errror:", self.hhmm)
        if all:
            for hhmm in self.hhmm:
                hhmm.show()
        else:
            self.hhmm[0].show()
    
    # roll over to next day, end actual day, print all lines
    def next_period(self):
        #print("next_period")
        n_wday = (self.actual + len(self.hhmm)-1)%6  # for 5 days: actual for hhmm[0], +4 for hhmm[4]
        # shift up: copy from line n to n+1 starting at end
        for i in range(len(self.hhmm)-2,-1,-1):  # 3,2,1,0  for 5 lines
            # copy actual day to next
            # print(i)
            values = self.hhmm[i].values
            # wday_text = Hour_Lines.intro[n_wday]
            wday_text = Hour_Lines.days[n_wday]            
            self.hhmm[i+1].set(values,wday_text)
            n_wday = n_wday -1 if n_wday > 0 else 6
            
        self.actual = (self.actual+1)%6
        wday_text = Hour_Lines.days[self.actual]            
        self.hhmm[0].set([0., -self.hourPlan, 0.], wday_text)         # new day az, +/- , break
    
    # roll over to monday, new week
    def new_week(self):
        self.actual = 0  # set to monday
        

class Hour_Line():
    """
    Provides:
        Objekt und Anzeige von einer Zeile jeweils: AZ, +/- und Pause als hh.mm
    """
    
    def __init__(self, x0, y0, color, dx, intro=''):
        self.hhmm = []  # will get 3 hh:mm display objects
        self.values = [0.,0.,0.]  # 3 float values for AZ, +/- and pause
        self.intro = intro
        self.day_text = ''
        self.y = y0
        
        x = x0
        line_hhmm=[]
        for i in range(3):
            # 3 hh:mm per line, 2nd is banlance with sign
            sign = False if i != 2 else True
            hhmm = HM(x, self.y, color=color, sign=sign)
            line_hhmm += [hhmm]
            x = hhmm.x_next + dx
        
        self.x_next = x
        self.hhmm = line_hhmm

    
    # Werte setzen
    def set(self, values, day_text=''):      # values as 3 float, day_text e.g. weekday
        self.values = values.copy()
        self.day_text = day_text
        self.show()

        
    # Anzeige der Zeile und update von values in hh:mm objekt mithilfe von SSEG output
    def show(self):
        UI.print(self.intro+self.day_text,self.y)
        if True: # use SSEG drawing for output 
            for i,hhmm in enumerate(self.hhmm):
                value = self.values[i]  # decimal value
                sign = ' '
                if value < 0:
                    value = abs(value)
                    sign = '-'
                value = min(99.99,value)
                hh = int(value)
                mm = int((value-hh)*60)
                hhmm_string = "%s%02d:%02d"%(sign,hh,mm)
                #hhmm_string = "%s%05.2f"%(sign,value)
                if False: # use SSEG drawing for output :
                    hhmm.set(hhmm_string)
                else:
                    x = hhmm.hh.sseg[0].pos_x
                    UI.print(hhmm_string, self.y, x)
        else:  # use UI.print for output
            x = len(self.intro+self.day_text) + 4
            x = self.hhmm[0].hhmm[0].hh.sseg[0].pos_x
            # create print line for all 3 time_h values 
            az,balance,brk = (11.2, -5.5, 0.25)
            triples = [MY_Time.convert2hms(t_h) for t_h in (az,balance,brk)]
            txt = tuple(["%2d:%2d"%trpl[:2] for trpl in triples])
            UI.print(txt, self.y, x)

    # use UI.print to generate output
    def print(self):
        pass
