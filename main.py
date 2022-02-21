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
#EMBEDDED = True
if 'micropython' in str(sys.implementation):
    EMBEDDED = True

import time
from LCD_7seg import SSEG, DIGITS, HM, debug_drawLine_fct
from worktime import WT_Day, WT_Week, Config, Logging, MY_Time

import machine
import framebuf
from Pico_LCD1_3 import LCD_1inch3
from LCD1_3_setup import *
SSEG.draf_fct = LCD.line

if EMBEDDED:
    pass

else:
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
COLOR = LCD.green if EMBEDDED else 0  # default when printing

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

class Show_Days():
    """
    Provides:
        Anzeige von 5 Zeilen jeweils: AZ, +/- und Pause
    """
    header = ['AZ','+/-', 'Pause'] # header line content
    days = ['Mo','Di','Mi','Do','Fr']
    intro = [' 0  ','-1  ','-2  ','-3  ','-4  ']
    
    def __init__(self, x0, y0, dx, color, lines=5, intro=None):  # x0 = 1st digit start, dx = separation between hh:mm
        self.hhmm = []  # will get 5 hh:mm display objects
        self.actual = 0  # pointer to actual day in days, 0 is monday
        intro = intro or Show_Days.intro.copy()
        
        for i in range(lines):
            line_hhmm = Show_PrintLine(x0, y0, color, dx, intro.pop(0))
            self.hhmm += [line_hhmm]
            y0  += SSEG.YSIZE  # next line y value
        self.y_next = y0
     
    # set defaults as worktime plan ...
    def setDefaults(self, dayPlan, weekPlan ):
        self.dayPlan = dayPlan
        self.weekPlan = weekPlan
    
    # update todays values and show
    def update(self, az,balance,breaktime):
        values = [az, balance, breaktime]
        wday = Show_Days.days[self.actual]
        self.hhmm[0].set(values, wday)
    
    # roll over to next day  (and end actual day)
    def next_day(self):
        n_wday = (self.actual + len(self.hhmm)-2)%6
        for i in range(len(self.hhmm)-2,0,-1):
            # copy actual day to next
            values = self.hhmm[i].values
            self.hhmm[i+1].set(values,Show_Days[n_wday])
            n_wday = n_wday -1 if n_wday > 0 else 6
            
        self.hhmm[0] = [0., -self.dayPlan, 0.]         # new day az, +/- , break
        self.actual = (self.actual+1)%6
    
    # roll over to monday, new week
    def new_week(self):
        self.actual = 0  # set to monday
        

class Show_PrintLine():
    """
    Provides:
        Anzeige von einer Zeile jeweils: AZ, +/- und Pause
    """
    
    def __init__(self, x0, y0, color, dx, intro=''):
        self.hhmm = []  # will get 3 hh:mm display objects
        self.values = []  # 3 float values for AZ, +/- and pause
        self.intro = intro
        self.y = y0
        
        x = x0
        line_hhmm=[]
        for i in range(3):
            # 3 hh:mm per line
            hhmm = HM(x, self.y, color=color)
            line_hhmm += [hhmm]
            x = hhmm.x_next + dx
        
        self.x_next = x
        self.hhmm = line_hhmm

    
    # Werte setzen und Anzeige der Zeile
    def set(self, values, pre_text=''):      # values as 3 float, pre_text e.g. weekday
        UI.print(self.intro+pre_text,self.y)
        self.values = values
        for hhmm in self.hhmm:
            value = values.pop(0)
            sign = ' '
            if value < 0:
                value = abs(value)
                sign = '-'
            value = min(99.99,value)
            hh = int(value)
            mm = (value-hh)*0.6
            hhmm_string = "%s%02d:%02d"%(sign,hh,mm)
            #hhmm_string = "%s%05.2f"%(sign,value)
            hhmm.set(hhmm_string)
        
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
            if CTRL.value()==0:              # joystick press
                return UI.key['setH']
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
    def print(cls, txt,y=10, x=8):
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
    
    ui_input = UI()
    wt_day =       WT_Day(work_time_plan=WORK_TIME_PLAN)
    wt_last_day =  WT_Day(work_time_plan=WORK_TIME_PLAN)
    wt_week =      WT_Week(work_time_plan=WORK_TIME_PLAN)    
    wt_last_week = WT_Week(work_time_plan=WORK_TIME_PLAN)
    
    UI.FBUF = LCD
    ssColor = LCD.white
    
    SSEG.setSize(x_digit_separation=4, x_digit_size=10, y_digit_separation=4, y_digit_size=14)
    dx=10 + 14*4  # distance between hh:mm objects
    dy=18  # Line spacing

    y0 = dy     # first line with digits
    x0 = len('Tag WTag')*8+2*8    # x-pos first hh:mm  (AZ)
    
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

    UI.print("Tag WTag  AZ    +/-  Pause",y)
    days = Show_Days(x0,y0,ssColor, dx)
    y = days.y_next
    weeks = Show_Days(x,y0,ssColor, dx, lines=2, intro=['Woche','Wo-1'])
    UI.print("Sollzeit: 35h",200)

#%%
        
        
    #digits = [SSEG(10,200,ssColor,UI.drawLine), SSEG(20,200,ssColor,UI.drawLine)]

    #hh = DIGITS(2, x0, y0, color=ssColor, right_separator=':')    
    #hh.set('59')
    
    #hm = HM(x0+50, y0, color=ssColor) 
    #hm.set('15:43')

    #hm2y = hm.y_next + SSEG.YSIZE
    #hm2 = HM(x0+50, hm2y, color=ssColor) 
    #hm2.set('04:11')


    #d = SSEG(50,180,LCD.white)
    #d.draw_segment('tr')
    #d.draw_segment('br')
    #d.clear()
    #d.set(5)
    #d.clear()
    #d.draw_segment('tr',True)

    #digits[0].set('1')
    #digits[1].set(0)
    
    #LCD.line(10, 180, 30, 180, LCD.red)
    #LCD.line(100, 180, 100, 220, LCD.blue)

#%%    
    while True:
        TIME_H, TIME_WD = MY_Time.getLocaltime()        

        if UI.query():
            KEY_CHR = ''
            key = UI.getKey()

            if   key == UI.key['start']:
                # top key
                wt_day.startWork(TIME_H)
                COLOR = LCD.green

            elif key == UI.key['stop']:
                # bottom key
                wt_day.stopWork(TIME_H)
                COLOR = LCD.red

            elif key == UI.key['resetTotal']:
                # 2nd key from top
                # reset accumulated total work time
                TOTAL_WT = 0.

            elif key == UI.key['setWd']:
                # set week day
                if EMBEDDED:
                    pass
                else:
                    new_wd = input("Working Day 0...6: ")
                    TIME_WD = MY_Time.setWd(int(new_wd))
                Config.write()

            elif key == UI.key['setH']:
                # joystick press
                # set hour from user input or simply to 12:00
                if EMBEDDED:
                    TIME_H = MY_Time.setH(int(12))
                else:
                    new_hour = input("Hour 0...23: ")
                    TIME_H = MY_Time.setH(int(new_hour))
                
            elif key == UI.key['setH0']:
                # set minutes/seconds to 00:00
                hour = round(TIME_H)
                TIME_H = MY_Time.setH0(hour)

            elif key == UI.key['setPlan']:
                # set planned work time / week
                if EMBEDDED:
                    pass
                else:
                    wtp = input("Hours/week 0..40.5: ")
                
                WORK_TIME_PLAN = wtp
                WT_Day.set_Wt_Plan(wtp)
                WT_Week.work_time_plan = wtp
                Config.write()

            elif key == UI.key['setEndDay']:
                # 3rd from top
                # set TIME_H = 23.90
                time_h = 23.978
                TIME_H, TIME_WD = MY_Time.changeTime(time_h)

        
        # endif ui_query
        
        wt_day.update(TIME_H)        
        wt_week.update()
                    
        # LCD Output
        if EMBEDDED:
            _sec = time.mktime(tuple(MY_Time.localTimeTuple))
            _tt = time.localtime(_sec)
            #UI.print("UI print test %d"%222,30)
            # strftime not in micropython
            #UI.print("%s  Hour %.4f  weekDay %d"%(time.strftime("%d.%m %H:%M:%S",_tt),TIME_H, TIME_WD),10)
            UI.print("%s  Hour %.2f  weekDay %d"%('datum',TIME_H, TIME_WD),10)
            UI.print("Today Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_day.totalBalance,wt_day.totalBreak, wt_day.totalHours),30)
            UI.print("yest  Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_last_day.totalBalance,wt_last_day.totalBreak, wt_last_day.totalHours),50)
            UI.print("Week  Balance %d"%0, 70)
            UI.print("Last Wk Balan %d "%0, 90)
            ss = "%.3f"%TIME_H
            ss = ss[-2:]
            UI.print("xxxx %s"%ss,110)
            #ss = "34"
            # UI.printNumber(ss, digits=digits)
            days.update(az=wt_day.totalHours, balance=wt_day.totalBalance, breaktime=wt_day.totalBreak)
            
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
        if TIME_H >= 23.98 and dayEndProcessed == False:  # last minute
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
            if TIME_WD == 4:             
                # Friday end of day
                if not EMBEDDED:
                    print("Week Ended")
                wt_last_week = wt_week
                wt_week = WT_Week(work_time_plan=WORK_TIME_PLAN)    

        if TIME_H < 0.1:
            dayEndProcessed = False
            
        if EMBEDDED:
            time.sleep_ms(200)
            
#######################################################
#%%
if __name__ == '__main__':     
    main()
      
