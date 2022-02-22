#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 11:04:13 2022

@author: urban


Pico ZeitUhr

Erfasse Arbeitszeit (AZ) und Zeige Werte als Hilfe zur Zeitbuchungskorrektur
Zeige AZ- Soll
    aktuelle Tag
    letzte Tag
    aktuelle Woche (ohne heute)
    letzte Woche
    Summe alles  (ohne heute)
         
UI:
    Setze Wochentag  (Mo..Fr)
    Setze Stunde  (0..24)
    Setzte Minuten/Sek auf 0
    Setzte Sollzeit (h, 1 Dezimalstelle, default = 35.0h)
    Lösche AZ Summe  (bis Vortag, aktuelle Tag bleibt)
    start / stop

Daten:
    Speichere settings in config.csv
    Speichere Tages und Wochendaten in AZtage.csv (Datum, WoTag, Start, Stop, Pausenzeit, Salden. Fortlaufend)
        bzw. AZwoche.csv (kw_xxx, Datum Start, AZ, Pause, Saldo)

AZ-Model:
    0.5h Pause täglich abgezogen. Wenn AZ-pause --> darin berücksichtigen
    wenn AZ > 6h --> weitere 0.25h Abzug.   AZ-pausen ebenfalls berücksichtigen

Optional:
    Presence Sensor: Starte / Stoppe Arbeitszeit
    
Screen layout:
     for LCD 1,3" color display, 240x240 pixel

"""

#%%
#####################################################
import sys, os

EMBEDDED = False  # set True if running embedded (>enables io-port, RTC time setting, display out)
EMBEDDED = True
if 'micropython' in str(sys.implementation):
    EMBEDDED = True
    
_SSEG = True  # is 7seg- implementation used for output, or simple print to framebuffer
#_SSEG = False    

#%%
import time
from LCD_7seg import SSEG, DIGITS, HM, debug_drawLine_fct
from worktime import WT_Day, WT_Week, Config, Logging, MY_Time

import machine
import framebuf
from Pico_LCD1_3 import LCD_1inch3
from LCD1_3_setup import *

if EMBEDDED:
    pass

else:
    worktime.EMBEDDED = False
#    import keyboard    # requires root for operation !!!!!
#    def getchr():
#        return keyboard.read_key()   
    import pynput
    KEY_CHR = ''
    def on_press(key='I'): global KEY_CHR; KEY_CHR=key
    def on_release(key=''): global KEY_CHR; KEY_CHR=''
    def on_scroll(x,y,dx,dy): global KEY_CHR; KEY_CHR='I'
    # A helper function when delegating on_press/on_release events
    if False:
        # all keyboard listeners do not work in spyder IDE !
        def for_canonical(f): return lambda k: f(l.canonical(k))
        hotkey = pynput.keyboard.HotKey(['I'], on_press)
        listener = pynput.keyboard.Listener(
            on_press=hotkey.press,
            on_release=hotkey.release )
    listener = pynput.mouse.Listener(
        on_scroll=on_scroll)
    listener.start()
    
        
#    listener = pynput.keyboard.Listener(
#        on_press=on_press(key),
#        on_release=on_release(key) )  
#    listener.start()

#    with pynput.keyboard.Listener(
#    on_press=on_press(key),
#    on_release=on_release(key) ) as listener:
#        listener.join()

#####################################################

TIME_H = 0.     # actual hour (decimal)
TIME_WD = 0     # actual week day (0 = Monday)
TOTAL_WT = 0.   # accumulated work time - planned worktime
WORK_TIME_PLAN = 35.0 # work time per hour plan
COLOR = LCD.red if EMBEDDED else 0  # default when starting day: pause condition

#%%    
#####################################################

class UI():
    """
    Provides:
        UI input events sowie Eingabe support
    """

    key={'start':'a',                 # mapping internal function to received key press 'ids'
         'stop':'o',
         'setH':'h',
         'setH0':'0',
         'setWd':'w',
         'setPlan':'p',
         'resetTotal':'r',
         'setEndDay':'e'
         }
    
    FBUF = None                       # set to lcd object (inherits framebuf.FrameBuffer)
    
    @classmethod
    def query(cls):
        global KEY_CHR
        if EMBEDDED:
            for key in [KEYA,KEYB,KEYX, KEYY,CTRL]:
                if key.value()==0:
                    return True
            return False
        else:
            if KEY_CHR != '':
                KEY_CHR = ''
                return True
            else:
                return False
        
    @classmethod
    def getKey(cls):
        if EMBEDDED:
            if KEYA.value()==0:           
                return UI.key['start']    # top key
            if KEYY.value()==0:            
                return UI.key['stop']     # bottom key
            if KEYB.value()==0:
                return UI.key['resetTotal']  # 2nd from top
            if KEYX.value()==0:
                return UI.key['setEndDay']   # 3rd from top
            if CTRL.value()==0:              
                return UI.key['setH']        # joystick press: setH to 12h
        else:
            key = input("enter input key start|stop|resetTotal|setWd|setH|setH0|setEndDay : ")
            # return key
            if not key in UI.key:
                return ''
            return UI.key[key]
        
    @classmethod
    def getMove(cls):
        if EMBEDDED:
            if LEFT.value()==0:           
                return UI.key['start']       # next field
            if RIGHT.value()==0:            
                return UI.key['stop']        # prev field
            if UP.value()==0:
                return UI.key['resetTotal']  # increment
            if DOWN.value()==0:
                return UI.key['setEndDay']   # decrement
            if CTRL.value()==0:           
                return UI.key['setH']        # enter
            return None
        else:
            return None
        
    @classmethod
    def print(cls, txt, y=0, x=0):
        if EMBEDDED:
            _txt=str(txt)
            LCD.text(_txt,int(x),int(y),COLOR)    # x,y  from top left corner
            LCD.show()
        else:
            print(txt)

    @classmethod            
    def printNumber(cls, num_txt, digits=[]):   # digits is list of SSEG objects
        for i,ss in enumerate(digits):
            if i < len(num_txt):
                d = num_txt[i]
                #ss = digits[i]
                ss.set(d,pt=False)
            else:
                ss.clear()

    @classmethod    
    def drawLine(cls,p1, p2, color):
        # color=LCD.white
        if EMBEDDED:
            # FrameBuffer.line(x1, y1, x2, y2, c)
            UI.FBUF.line(p1[0], p1[1], p2[0], p2[1], color)
        else:
            debug_drawLine_fct(p1[0], p1[1], p2[0], p2[1], color)
            

class UI_():
    @classmethod
    def print(cls, txt,y=10, x=8):
        print(x,y,txt)
        _txt=str(txt)
        LCD.text(_txt,int(x),int(y),COLOR)    # x,y  from top left corner
        LCD.show()

#%%        
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
    days = ['Mo','Di','Mi','Do','Fr']             # 2nd position start text for lines
    
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
        

#####################################################
    
def main():
    global TIME_H, TIME_WD, TOTAL_WT, WORK_TIME_PLAN, KEY_CHR, COLOR
    print("start main")
    
    if EMBEDDED:
        MY_Time.RTC = machine.RTC()
    
    config = Config()
#%%
    Config.read()
    
    WORK_TIME_PLAN = Config.workTimePlan
    KEY_CHR = ''
    dayEndProcessed = False

    # setup display out
    # 
    
    LCD.lightBlue = (0x1f << 11) + (0x06 <<6) + 0x06    # 5 bit, order = brg
    ui_input = UI()
    wt_day =       WT_Day(work_time_plan=WORK_TIME_PLAN)
    wt_last_day =  WT_Day(work_time_plan=WORK_TIME_PLAN)
    wt_week =      WT_Week(work_time_plan=WORK_TIME_PLAN)    
    wt_last_week = WT_Week(work_time_plan=WORK_TIME_PLAN)
    
    UI.FBUF = LCD
    ssColor = LCD.white
    SSEG.drawLine_fct = LCD.line
    SSEG.setSize(x_digit_separation=5, x_digit_size=8, y_digit_separation=4, y_digit_size=14)
    
    dx=22 #10 + 14*4  # distance between hh:mm objects
    dy=18+2  # Line spacing

    y0 = dy * 2     # first line with digits bottom position = 2x spacing
    x0 = 28 #len('Tag WTag')*8+2*8    # x-pos first hh:mm  (AZ)
    
    # Output format is
    '''
    Tag WTag  AZ     Pause  +/-
    0   Fr    00:00  00:00  00:00
    -1  Do    
    -2  Mi
    -3  Di
    -4  Mo
    Woche     00:00  00:00  00:00
    W-1       00:00  00:00  00:00
    Sollzeit: 35h
    '''
    
    y = y0
    x = x0

    #  setup UI output
    UI.print("Tag WD  AZ  +/-  Pause",0)
    days = Hour_Lines(x0,y0, dx=dx, dy=dy, color=ssColor)
    days.setPlan(WORK_TIME_PLAN)

    y = days.y_next
    weeks = Hour_Lines(x,y, dx=dx, dy=dy, color=ssColor, lines=2, intro=['W0  ','W-1 '])
    weeks.setPlan(WORK_TIME_PLAN*5)
    
    clock = HM(120, 239-dy, color=LCD.lightBlue, sign=False, n=3)

    UI.print("Sollzeit: 35h",220)    

    print("setup finished")
    #print("days", days.hhmm)
    #print("weeks", weeks.hhmm)
    values = [1., 2., 3.]
    
    """
    s0 = Hour_Line(x0, y0, LCD.white, dx, intro='Hi')
    s0.set([1., 3., 5.], 'Mo')
    s0.show()
    s1 = Hour_Line(x0, y0+dy, LCD.white, dx, intro='Ho')
    s1.set([10.1, 13.3, 15.5], 'Mo')
    s1.show()    
    while(1):
        values[0] += 0.1
        values[1] += 0.01
        time.sleep_ms(1000)
        s0.set(values, 'xx')
        s1.set(values, 'xx')
        s0.show()
        s1.show()
        print(values)
    """
    
    """
    h0=days.hhmm[0]
    h0.show()

    
    values = [1., 2., 3.]
    while(1):
        values[0] += 0.1
        time.sleep_ms(1000)
        h0.set(values, 'xx')
        h0.show()
        print(values)
    """  
    
#%%    
    while True:
        TIME_H, TIME_WD = MY_Time.getLocaltime()        

        if UI.query():
            KEY_CHR = ''
            key = UI.getKey()

            if   key == UI.key['start']:                # top key:    start work
                wt_day.startWork(TIME_H)
                COLOR = LCD.green

            elif key == UI.key['stop']:                 # bottom key: pause
                wt_day.stopWork(TIME_H)
                COLOR = LCD.red

            elif key == UI.key['resetTotal']:           # 2nd key from top : reset accumulated total work time
                TOTAL_WT = 0.

            elif key == UI.key['setWd']:                # not implemented:  set week day
                if EMBEDDED:
                    pass
                else:
                    new_wd = input("Working Day 0...6: ")
                    TIME_WD = MY_Time.setWd(int(new_wd))
                Config.write()

            elif key == UI.key['setH']:                 # joystick press:     set hour from user input (not embedded) or simply to 12:00
                if EMBEDDED:
                    TIME_H = MY_Time.setH(int(12))
                else:
                    new_hour = input("Hour 0...23: ")
                    TIME_H = MY_Time.setH(int(new_hour))
                
            elif key == UI.key['setH0']:                # not implemented:     set minutes/seconds to 00:00
                hour = round(TIME_H)
                TIME_H = MY_Time.setH0(hour)

            elif key == UI.key['setPlan']:              # not implemented:      set planned work time / week
                if EMBEDDED:
                    pass
                else:
                    wtp = input("Hours/week 0..40.5: ")
                
                WORK_TIME_PLAN = wtp
                WT_Day.set_Wt_Plan(wtp)
                WT_Week.work_time_plan = wtp
                Config.write()

            elif key == UI.key['setEndDay']:            # 3rd from top:   set TIME_H = 23:59:30
                time_h = 23.988
                TIME_H, TIME_WD = MY_Time.changeTime(time_h)
                COLOR = LCD.red

        
        # endif ui_query
        
        wt_day.update(TIME_H)        
        wt_week.update()
                    
        # LCD Output
        if EMBEDDED:
            _sec = time.mktime(tuple(MY_Time.localTimeTuple))
            _tt = time.localtime(_sec)
            
            if _SSEG:
                y=0
                UI.print("Day WD AZ   AZ +/-   Pause",x)
                y += dy                
                UI.print(" 0 %1d %.2f  %.2f  %.2f"%(wt_day.wd, wt_day.totalHours, wt_day.totalBalance,wt_day.totalBreak),y)
                UI.print(" 0 %1d %.2f  %.2f  %.2f"%(wt_last_day.wd, wt_last_day.totalHours, wt_last_day.totalBalance,wt_last_day.totalBreak),y+dy)

                
            if False:
                #UI.print("UI print test %d"%222,30)
                # strftime not in micropython
                #UI.print("%s  Hour %.4f  weekDay %d"%(time.strftime("%d.%m %H:%M:%S",_tt),TIME_H, TIME_WD),10)  # strftime not existing !
                # UI.print("%s  Hour %.2f  weekDay %d"%('datum',TIME_H, TIME_WD),10)
                #UI.print("Today Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_day.totalBalance,wt_day.totalBreak, wt_day.totalHours),30)
                #UI.print("yest  Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_last_day.totalBalance,wt_last_day.totalBreak, wt_last_day.totalHours),50)
                #UI.print("Week  Balance %d"%0, 70)
                #UI.print("Last Wk Balan %d "%0, 90)
                pass
            ss = "%.3f"%TIME_H
            ss = ss[-2:]
            # UI.print("xxxx %s"%ss,110)
            #ss = "34"
            # UI.printNumber(ss, digits=digits)
            #print(_sec)

            days.update(az=wt_day.totalHours, balance=wt_day.totalBalance, breaktime=wt_day.totalBreak)
            weeks.update(az=wt_week.totalWt, balance=wt_week.totalBalance, breaktime=wt_week.totalBreak)

            if int(_sec) % 5 == 0:
                print("update clock")
                if _SSEG:
                    days.show()
                    hh,mm,ss = MY_Time.localTimeTuple[3:6]
                    hhmmss = "%2d:%2d:%2d"%(hh,mm,ss)
                    clock.set(hhmmss)

            if int(_sec) % 60 == 0:
                if _SSEG:
                    weeks.show(all=True)
            
        else:
            _sec = time.mktime(tuple(MY_Time.localTimeTuple))
            _tt = time.localtime(_sec)                    
            print("%s  Hour %.4f  weekDay %d"%(time.strftime("%d.%m %H:%M:%S",_tt),TIME_H, TIME_WD))
            print("    Today Balance %.4f  Brakes %.4f  Hours %.4f"%(wt_day.totalBalance,wt_day.totalBreak, wt_day.totalHours))
            print("Yesterday Balance %.4f  Brakes %.4f  Hours %.4f"%(wt_last_day.totalBalance,wt_last_day.totalBreak, wt_last_day.totalHours))
            print("Week Balance",0)
            print("Last Week Balance",0)
        
        # process presence sensor input
        # tbd
        # trigger start or stop ...

        # end of day actions
        condition = (TIME_H >= 23.98)
        condition = ((TIME_H *60*60) % 20 == 0)  # debugging
        if condition and dayEndProcessed == False:  # last minute
            print("condition true")
            dayEndProcessed = True
            if not EMBEDDED:
                print("Day Ended")
            todays_wt = wt_day.endDay()
            Logging.write_day()
            wt_week.addDay(totalWt=wt_day.totalWt, totalBalance=wt_day.totalBalance, totalBreak=wt_day.totalBreak)
            Logging.write_week()
            Config.write()
            wt_last_day = wt_day
            wt_day =  WT_Day(work_time_plan=WORK_TIME_PLAN)
            # roll over days and print
            if _SSEG:
                days.next_period()  
            if TIME_WD == 4:             
                # Friday end of day
                print("wd == 4")
                if not EMBEDDED:
                    print("Week Ended")
                wt_last_week = wt_week
                wt_week = WT_Week(work_time_plan=WORK_TIME_PLAN)
                if _SSEG:                
                    days.new_week()
                    days.next_period()  
            if TIME_WD == 6:             
                # Sunday end of day
                if not EMBEDDED:
                    print("Week new")
                if _SSEG:
                    weeks.next_period()
            # print week and line
            if _SSEG:            
                days.show(all=True)  
                weeks.show(all=True)  
                UI.print("%s  Hour %.2f  weekDay %d"%('datum',TIME_H, TIME_WD),10)


        if TIME_H < 0.1:
            dayEndProcessed = False
            
        if EMBEDDED:
            time.sleep_ms(200)
            
#######################################################
#%%
if __name__ == '__main__':     
    main()
      
