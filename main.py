#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 11:04:13 2022

@author: urban


Pico ZeitUhr

Erfasse Arbeitszeit (AZ) und Zeige Werte als Hilfe zur Zeitbuchungskorrektur
Zeige AZ- Soll
    aktuelle Tag
    letzte Tag  (letzte 5 Tage)
    aktuelle Woche (ohne heute)
    letzte Woche
         
UI:
    Setze Wochentag  (Mo..Fr) über inc - dec
    Setze Stunde  (0..24)  über inc-dec
    Setzte Minuten/Sek auf 0  (mit Setze Stunde)
    Setzte Sollzeit (h, 1 Dezimalstelle, default = 35.0h)   (über config)
    Lösche AZ Summe  (bis Vortag, aktuelle Tag bleibt)
    start / stop (pause) / Tagesende

Daten:
    Speichere settings in config.json
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
######################################################
"""
to do

worktime unit tests in separate file

konzept für UI: Initial setup:  
    - Use case diagramme überlegen
    - Reset aktuelle Tag benötigt
    - Reset Balance (ohne änderung aktuelle Tag)

last_week und last days bekommen falsche werte ?

full (binary) storage and reload (pickle ?) von day, 5-day, week

Refactor von Berechnnungen wt_day  (ist z.Z. inkosistent)
- klare funktionen für update der Teilbereiche pause, Arbeitszeit,  balance ...
- fkt für anpassung zeit ohne dass sich Werte ändern (Uhr stellen ....)
- copy fkt für werte (z.B. aus status storage oder config storage)


klären was angezeigt wird, jeweils hh:mm oder hh.decimal ? 

"""
#####################################################
"""
Anzeige

Tages Balance Zeit       hh:mm             --> übersicht 
Tages Anwesenheitszeit   hh:mm
Tages Pause Zeit         hh:mm
Wochenzeiten             entsprechend

AZ_Korrektur             hh.dec            --> einfache Übernahme in BSH tool (AZ Ende bei tageskorrektur)
  hier klären ob mit 45' Pause oder ohne
Total_Balance            hh.dec            --> einfache Kontrolle wie BSH tool (bei tageskorrektur )

"""
#####################################################

"""
Use Case definitions

1. Start Work
    Arbeitstag starten oder nach Pause Fortsetzen
    -> AZ startet zählen
       Pause stop zählen, wird beended
    
2. Stop Work (Pause)
    Pause beginnen
    -> AZ stopt zählen
       Pausezeit zält
       
3. End Day
    Typisch: Tagesende
    Auch: Unterbrechung ohne Pause zählen
    Arbeitszeit Zählen stoppen.  Pausezeit nicht zählen
    -> AZ stopt zählen
       Pause stopt zählen, wird ggf. beendet
       
4. Reset Total Balance
    Balance von mehrern Tagen wird in BSH-SAP übernommen und hier gelöscht
    Das ganze findet währent Arbeitszeit eines Tages statt
    --> Aktuelle Arbeitstag wird nicht geändert
        --> total Balance ist nur von Vortagen ohne aktuelle Tag
        
5. Reset Aktuelle Tag
    Aktuelle Tag ist fehlerhaft oder wurde in total balance Übertrag -> bsh berücksichtigt
    --> aktuelle Tag wird so gesetzt dass today_balance zum aktuellen Zeitpunkt 0 ist. Pause auf 0, AZ=WorkHours auf ?
        workmode wird auf dayEnd gesetzt --> today_balance würde 0 bleiben
        Bei bedarf neu start Work --> balance wird ab 0 aktualisiert

6. Inc/Dec Time:Hour
    Uhrzeit eine Stunde vor / zurück. Dabei mm:ss auf 0
    --> Uhrzeit (als Folge ggf. Datum) ändern
        today balance soll unverändert bleiben
        
7. Inc/Dec week day
    Wochentag ändern. Uhrzeit unverändert lassen
    --> keine Änderung der AZ in allen Tagen / Wochen
        Anpassung Wochentagsanzeige heute
        nice-to-have: Anpassung wochentag in last-days 
        nice-to-have: Update der Wochen-salden
        
System use cases

11. Day rollover
    jeweils 23:59 automatisch
    --> Umschalten auf nä. Tag
        workmode auf endDay setzen (stop, keine Pause, keine Zeitstempel)
        last-days rollover 
        neue Tag initialisieren
        zustand und config speichern
        tages daten logging
            
12. week update
    jeweils Freitag abend nach day rollover
    --> wochensaldo berechnen
        wochen rollover
        wochen daten logging
        
"""

#####################################################
import sys, os

EMBEDDED = False  # set True if running embedded (>enables io-port, RTC time setting, display out)
EMBEDDED = True
if 'micropython' in str(sys.implementation):
    EMBEDDED = True
EMBEDDED_KEYS = True     # use False for python input triggered by mouse scroll whell instead of I/O query for keys
#EMBEDDED_KEYS = False
 
_SSEG = True  # is 7seg- implementation used for output, or simple print to framebuffer
_SSEG = False    

#%%
import time
from LCD_7seg import SSEG, DIGITS, HM, debug_drawLine_fct
from worktime import WT_Day, WT_Week, Config, Logging, MY_Time

import machine
import framebuf
from Pico_LCD1_3 import LCD_1inch3
from LCD1_3_setup import *                 # provides LCD, KEYxxx

if not EMBEDDED:
    import worktime  
    worktime.EMBEDDED = False
    
if not EMBEDDED_KEYS:
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
    # use mouse listener to activate input, works on spyder ide
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
# global variables
VERSION = 0.2

TIME_H = 0.     # actual hour (decimal)
TIME_WD = 0     # actual week day (0 = Monday)
BALANCE_PAST = 0. # accumulated work time balance past days
WORK_TIME_PLAN = 35.0 # work time per hour plan
COLOR = LCD.red if EMBEDDED else 0  # default when starting day: pause condition
WDAYS = ['Mo','Di','Mi','Do','Fr','Sa','So']    # shortcuts used for screen output
CONFIG = None   # config object
layout = None

# for debug: micropyton can access global variables after beeing stopped
wt_day = None; wt_recent=[]; wt_week=None; wt_last_week=None

#%%    
#####################################################

class UI():
    """
    Provides:
        UI input events sowie Eingabe support
    """

    key={'start':     'a',                 # mapping internal function to received key press 'ids' if not in embedded mode
         'stop':      'y',                 # ids are 1.3" LCD keys  A,B,X,Y and joystick up,down,left,right,ctrl
         'incH':      'u',
         'decH':      'd',
         'incWd':     'r',
         'decWd':     'l',
         'resetTotal':'b',
         'setEndDay': 'x',
         'store':     'c'
         }
    
    FBUF = None                       # set to lcd object (inherits framebuf.FrameBuffer)
    lastKey = ''
        
    @classmethod
    def query(cls):
        global KEY_CHR
        if EMBEDDED_KEYS:
            for key in [KEYA,KEYB,KEYX,KEYY, CTRL,UP,DOWN,LEFT,RIGHT]:
                if key.value()==0:
                    return True
            return False
        else:
            if KEY_CHR != '':                 # get by external event
                KEY_CHR = ''
                return True
            else:
                return False
        
    @classmethod
    def getKey(cls):
        if EMBEDDED_KEYS:
            if KEYA.value()==0:           
                return UI.key['start']       # top key
            if KEYY.value()==0:            
                return UI.key['stop']        # bottom key
            if KEYB.value()==0:
                return UI.key['resetTotal']  # 2nd from top
            if KEYX.value()==0:
                return UI.key['setEndDay']   # 3rd from top
            if CTRL.value()==0:           
                return UI.key['store']       # enter: store status to config
            if UP.value()==0:              
                return UI.key['incH']        # joystick up: inc hour (mm:ss == 0)
            if DOWN.value()==0:              
                return UI.key['decH']        # joystick down: dec hour (mm:ss == 0)
            if RIGHT.value()==0:              
                return UI.key['incWd']       # joystick right: inc week day
            if LEFT.value()==0:              
                return UI.key['decWd']       # joystick left: dec week day
        else:
            key = input("enter input key start|stop|incH|decH|incWd|decWd|resetTotal|setEndDay/store : ")
            # return key
            if not key in UI.key:
                return ''
            return UI.key[key]


    @classmethod
    def action(cls, *args):  #, wt_day, wt_recent, wt_week, wt_last_week):
        global COLOR, TIME_H, TIME_WD, BALANCE_PAST, CONFIG, layout
        global  wt_day, wt_recent, wt_week, wt_last_week
        if not UI.query():
            UI.lastKey = ''
        else:
            KEY_CHR = ''
            key = UI.getKey()
            if key:
                print(key)

            # special combined presses for debugging
            if key == UI.key['resetTotal'] and UI.lastKey == UI.key['start']: # down + 2nd key --> enter micropython console mode by forcing crah
                print(execution_ended)
            if key == UI.key['setEndDay'] and UI.lastKey == UI.key['start']: # down + 3rd key --> simulate day end
                print("set to 23:59:30")
                wt_day.stopWork(TIME_H)
                wt_day.endDay()
                new_time = 23.9917
                TIME_H, TIME_WD = MY_Time.setTime(new_time)
                key = ''

            if key == UI.key['start']:                  # top key:    start work
                wt_day.startWork(TIME_H)
                COLOR = LCD.green
                balance = wt_day.totalBalance
                CONFIG.config['balance_today'] = balance
                #CONFIG.write()

            elif key == UI.key['stop']:                 # bottom key:  pause
                wt_day.stopWork(TIME_H)
                COLOR = LCD.red # LCD.orange
                balance = wt_day.totalBalance
                CONFIG.config['balance_today'] = balance
                #CONFIG.write()

            elif key == UI.key['resetTotal']:           # 2nd key from top : reset past balance (and today ?) 
                BALANCE_PAST = 0.
                CONFIG.config['balance_past'] = 0.
                # reset current day
                # wt_day =  WT_Day(work_time_plan=WORK_TIME_PLAN)

            elif key == UI.key['incWd']:                # joystick right:   increment week day
                TIME_WD = MY_Time.changeDate(+1)
                wt_day.wd = TIME_WD
                date = MY_Time.localTimeTuple[0:3]
                CONFIG.config['date'] = date
                #CONFIG.write()

            elif key == UI.key['decWd']:                # joystick left:    decrement week day
                TIME_WD = MY_Time.changeDate(-1)
                wt_day.wd = TIME_WD
                date = MY_Time.localTimeTuple[0:3]
                CONFIG.config['date'] = date
                #CONFIG.write()

            elif key == UI.key['incH']:                 # joystick up:      increment hour, mm:ss == 0
                new_time = round(TIME_H + 0.5)
                TIME_H = MY_Time.setH0(new_time)
                CONFIG.config['time'] = TIME_H
                #CONFIG.write()

            elif key == UI.key['decH']:                 # joystick down:    decrement hour, mm:ss == 0
                new_time = round(TIME_H - 1.)
                TIME_H = MY_Time.setH0(new_time)
                CONFIG.config['time'] = TIME_H
                #CONFIG.write()

            elif key == UI.key['store']:                # joystick press:    store actual to config
                date = MY_Time.localTimeTuple[0:3]
                CONFIG.updateState(wt_day, time=TIME_H, date=date)
                CONFIG.write()
                # Logging.write_day(MY_Time.localTimeTuple, [wt_day.totalWt, wt_day.totalBalance, wt_day.totalHours, wt_day.start])            
                
            elif key == UI.key['setEndDay']:            # 3rd from top:   end worktime,stop pause counting
                #time_h = 23.988
                #TIME_H, TIME_WD = MY_Time.setTime(time_h)
                wt_day.stopWork(TIME_H)
                wt_day.endDay()
                COLOR = LCD.white

                balance = wt_day.totalBalance
                date = MY_Time.localTimeTuple[0:3]
                CONFIG.config['balance_today'] = balance
                CONFIG.config['time'] = TIME_H
                CONFIG.config['date'] = date
                CONFIG.write()


            screen_update(wt_day, wt_recent, wt_week, wt_last_week, layout)
            UI.lastKey = key


        
    @classmethod
    def print(cls, txt, y=0, x=0):
        if EMBEDDED:
            _txt=str(txt)
            LCD.text(chr(219)*len(_txt),int(x),int(y),0x00)    # try to clear before using ascii block character     
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


    # print one line with 3 tuples of (az,balance,break)
    @classmethod    
    def printLine(cls, values, x=0, y=0, intro_txt='', n_wday=0):

        n_wday = n_wday%7
        wday_txt = WDAYS[n_wday]
                 
        # create print line for all 3 time_h values 
        # values = (11.2, -5.5, 0.25)
        triples = [MY_Time.convert2hms(t_h) for t_h in values]
        txt = tuple(["%2d:%02d"%trpl[:2] for trpl in triples])
        txt = '  '.join(txt)
         
        UI.print(' '.join([intro_txt,wday_txt,txt]), y=y)
            

class UI_():
    @classmethod
    def print(cls, txt,y=10, x=8):
        print(x,y,txt)
        _txt=str(txt)
        LCD.text(_txt,int(x),int(y),COLOR)    # x,y  from top left corner
        LCD.show()

#########################################################

def screen_update(wt_day, wt_recent, wt_week, wt_last_week, layout):
    global EMBEDDED
    
    if not EMBEDDED:
        _screen_update_nonEmbedded(wt_day, wt_recent, wt_week, wt_last_week, layout)
        return
    
    dy = layout['dy']
    y0 = layout['y0']
    x0 = layout['x0']

    # LCD Output        
    if True:
        #  direkte output per UI.print, keine SSEG
        UI.print("    WD  AZ     +/-    Pause",0)

        # day summaries
        n_wday=wt_day.wd
        y = y0 + dy    
        UI.printLine(wt_day.getValues(),x=x0, y=y, intro_txt=' 0 ', n_wday=n_wday)
        y += dy    
        for i in range(4):
            UI.printLine(wt_recent[i].getValues(),x=x0, y=y, intro_txt=str(-i-1)+' ', n_wday=int(n_wday-1-i))
            y += dy    
        # week summaries
        UI.printLine(wt_week.getValues(),x=x0, y=y+dy, intro_txt=' W0', n_wday=0)
        UI.printLine(wt_last_week.getValues(),x=x0, y=y+2*dy, intro_txt='W-1', n_wday=0)
        y = y+4*dy

        # clock and ....
        hh,mm,ss = MY_Time.localTimeTuple[3:6]
        hhmmss = "%02d:%02d:%02d"%(hh,mm,ss)
        total_balance = BALANCE_PAST + wt_day.totalBalance
        UI.print(hhmmss+" Tot=%1.2f Pla=%1.2f"%(total_balance, wt_day.wtPlan),y)
        UI.print("v%1.1f"%(VERSION),y+dy, x=200)
        
    if False:
        #UI.print("UI print test %d"%222,30)
        # strftime not in micropython
        #UI.print("%s  Hour %.4f  weekDay %d"%(time.strftime("%d.%m %H:%M:%S",_tt),TIME_H, TIME_WD),10)  # strftime not existing !
        # UI.print("%s  Hour %.2f  weekDay %d"%('datum',TIME_H, TIME_WD),10)
        #UI.print("Today Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_day.totalBalance,wt_day.totalBreak, wt_day.totalWt),30)
        #UI.print("yest  Balance %.3f  Brakes %.3f  Hours %.4f"%(wt_last_day.totalBalance,wt_last_day.totalBreak, wt_last_day.totalWt),50)
        #UI.print("Week  Balance %d"%0, 70)
        #UI.print("Last Wk Balan %d "%0, 90)

        ss = "%.3f"%TIME_H
        ss = ss[-2:]

                        
def _screen_update_nonEmbedded(wt_day, wt_recent, wt_week, wt_last_week, layout):
    _sec = time.mktime(tuple(MY_Time.localTimeTuple))
    _tt = time.localtime(_sec)                    
    print("%s  Hour %.4f  weekDay %d"%(time.strftime("%d.%m %H:%M:%S",_tt),TIME_H, TIME_WD))
    print("    Today Balance %.4f  Brakes %.4f  Hours %.4f"%(wt_day.totalBalance,wt_day.totalBreak, wt_day.totalWt))
    print("Yesterday Balance %.4f  Brakes %.4f  Hours %.4f"%(wt_last_day.totalBalance,wt_last_day.totalBreak, wt_last_day.totalWt))
    print("Week Balance",0)
    print("Last Week Balance",0)


#%%
#####################################################
    
def main():
    global TIME_H, TIME_WD, BALANCE_PAST, WORK_TIME_PLAN, KEY_CHR, COLOR, CONFIG, layout
    global wt_day, wt_recent, wt_week, wt_last_week
    print("start main")

#%%    
    print(EMBEDDED_KEYS)
    MY_Time.RTC = machine.RTC()
    
    ls = os.listdir('/')
    print("ls: ", ls)
    CONFIG = Config()  # only class methods, no real instances ...
    config = CONFIG.read()
    print(config)
    
    WORK_TIME_PLAN = config['workTimePlan']
    WT_Day.set_Wt_Plan(WORK_TIME_PLAN)
    WT_Day.wtMinBreak = config['breakTime']
    KEY_CHR = ''

    # n_wd = MY_Time.localTimeTuple[6]  # actual week day
    date = config['date']
    TIME_WD = MY_Time.setDate(date)    
    TIME_H, TIME_WD = MY_Time.setTime(config['time'])
    print(TIME_H)


    # setup display out
    COLOR = LCD.white     # start in dayEnd mode
    ui_input = UI()

    # setup worktime objects
    wt_day =  WT_Day(work_time_plan=WORK_TIME_PLAN, time_wd = TIME_WD)
    wt_day.reset2Balance(config['balance_today'])
    BALANCE_PAST = config['balance_past']
    wt_recent = []
    for i in range(4):
        wt_recent  +=  [WT_Day(work_time_plan=WORK_TIME_PLAN)]
    wt_week =      WT_Week(work_time_plan=WORK_TIME_PLAN)    
    wt_last_week = WT_Week(work_time_plan=WORK_TIME_PLAN)
    
    UI.FBUF = LCD
    ssColor = LCD.white
    #SSEG.drawLine_fct = LCD.line
    #SSEG.setSize(x_digit_separation=5, x_digit_size=8, y_digit_separation=4, y_digit_size=14)
    
    dx=22 #10 + 14*4  # distance between hh:mm objects
    dy=18+2  # Line spacing
    y0 = dy * 2     # first line with digits bottom position = 2x spacing
    x0 = 28 #len('Tag WTag')*8+2*8    # x-pos first hh:mm  (AZ)
    
    layout = {  'dx':dx,
                'x0':0,
                'y0':0,
                'dy':dy
        }
        

    #  setup LCD UI output
    if False:
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
        
    ################################################
    update = True
    processDayEnd = True

#%%
    print("start while")
    while True:
        TIME_H, TIME_WD = MY_Time.getLocaltime()        
        _sec = time.mktime(tuple(MY_Time.localTimeTuple))
        _tt = time.localtime(_sec)
        
        # react to key press
        UI.action(wt_day, wt_recent, wt_week, wt_last_week)
               
        wt_day.update(TIME_H)        
        wt_week.update(totalWt=wt_day.totalWt, totalBalance=wt_day.totalBalance, totalBreak=wt_day.totalBreak)
                    
        # screen refresh every 10 sec.
        if int(_sec) % 10 == 0 and update:
            LCD.fill(0x0000)
            screen_update(wt_day, wt_recent, wt_week, wt_last_week, layout)

        # config and actual balance save every hour
        if int(_sec) % (60*60) == 0 and update:
            date = MY_Time.localTimeTuple[0:3]
            CONFIG.updateState(wt_day, time=TIME_H, date=date)
            CONFIG.write()


        # enable next screen update
        if int(_sec) % 3 == 1:
            update = True

        # screen update every 3 sec.
        if int(_sec) % 3 == 0 and update:
            update = False
            screen_update(wt_day, wt_recent, wt_week, wt_last_week, layout)
                        
        # process presence sensor input
        # tbd
        # trigger start or stop ...

        # end of day actions
        condition = (TIME_H >= 23.98)
        #condition = ((TIME_H *60*60) % 20 == 0)  # debugging
        if condition and processDayEnd == True:  # last minute
            print("condition day end @ sec=", _sec)
            processDayEnd = False
            todays_wt = wt_day.endDay()
            Logging.write_day(MY_Time.localTimeTuple, [wt_day.totalWt, wt_day.totalBalance, wt_day.totalHours, wt_day.start])            
            wt_week.addDay(totalWt=wt_day.totalWt, totalBalance=wt_day.totalBalance, totalBreak=wt_day.totalBreak)
            CONFIG.write()
            
            # fifo wt_recent update
            wt_recent.pop()   # pop() = remove last entry
            wt_recent = [wt_day] + wt_recent
            wt_day =  WT_Day(work_time_plan=WORK_TIME_PLAN)
            COLOR = LCD.white

            # roll over days
            if TIME_WD == 4:          # Friday end of day
                print("Friday: wd == 4")
                wt_last_week = wt_week
                wt_week = WT_Week(work_time_plan=WORK_TIME_PLAN)
                Logging.write_week(MY_Time.localTimeTuple, [wt_week.totalWt, wt_week.totalBalance])
            if TIME_WD == 6:             
                # Sunday end of day
                print("New Week")

        if TIME_H < 0.0083:
            processDayEnd = True
            
        if EMBEDDED:
            time.sleep_ms(200)
        else:
            time.sleep(0.2)

  
#######################################################
 
#%%
if __name__ == '__main__':     
    main()
      
