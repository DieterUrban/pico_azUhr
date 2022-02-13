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

"""

#%%
#####################################################
import sys, os
import time

EMBEDDED = False  # set True if running embedded (>enables io-port, RTC time setting, display out)
if 'micropython' in sys.implementation:
    EMBEDDED = True

if EMBEDDED:
    import machine
    from Pico_LCD1_3 import LCD_1inch3
    import framebuf
    
    from LCD1_3_setup import *
    
    '''
    BL = 13
    DC = 8
    RST = 12
    MOSI = 11
    SCK = 10
    CS = 9

    pwm = PWM(Pin(BL))
    pwm.freq(1000)
    pwm.duty_u16(32768)#max 65535

    LCD = LCD_1inch3()
    #color BRG
    LCD.fill(0x0000)
    LCD.show()

    KEYA = Pin(15,Pin.IN,Pin.PULL_UP)
    KEYB = Pin(17,Pin.IN,Pin.PULL_UP)
    KEYX = Pin(19 ,Pin.IN,Pin.PULL_UP)
    KEYY= Pin(21 ,Pin.IN,Pin.PULL_UP)

    UP = Pin(2,Pin.IN,Pin.PULL_UP)
    DOWN = Pin(18,Pin.IN,Pin.PULL_UP)
    LEFT = Pin(16,Pin.IN,Pin.PULL_UP)
    RIGHT = Pin(20,Pin.IN,Pin.PULL_UP)
    CTRL = Pin(3,Pin.IN,Pin.PULL_UP)
    '''

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
COLOR = LCD.green  # default when printing

#####################################################

class WT_Day():
    """
    Provides:
        Zeitdaten eines Tages sowie Methoden rund um Zeiteinträge
    """
    wd = 0           # week day (0 = Monday)
    start = -1.      # todays hour decimal first start time
    stop = -1.       # todays hour decimal final stop time
    actualStart = -1.  # recent start time (e.g. after break)
    actualStop = -1.   # recent stop time
    wtPlan = 0.        # work time per day plan
    totalWtLastStop = 0.  # total working hours excluding breaks up to last stop
    totalWt = 0.       # total working hours excluding breaks up to actual time
    totalBalance = 0.  # work time balance up to actual time
    totalHours = 0.    # total time stop - start
    totalBreak = 0.    # break time entered by user  (actual break will not be included unless work started again or day ended)
    working = False    # work or break/endOfWork status
    
    @classmethod
    def set_Wt_Plan(cls, work_time_plan):
        cls.wtPlan = round(work_time_plan/5.,2)

    def __init__(self, time_wd=0, 
                       work_time_plan=WORK_TIME_PLAN):
        WT_Day.set_Wt_Plan(work_time_plan)
        self.wd = time_wd    # week day    
    
    def startWork(self, time_h=0.):
        """
        Set start work timestamp. 
        If not first --> end break and update break time
        """
        self.working = True
        if self.start < 0:
            self.start = time_h
        if self.actualStop >= 0:
            # update break time
            breakTime = time_h - self.actualStop
            self.totalBreak += breakTime
        self.actualStart = time_h
        
    
    def stopWork(self, time_h=0.):
        """
        Set stop work timestamp. 
        Update totalWT = total Worktime
        """
        if self.start < 0:
            # stop before start ... do nothing
            return
        if self.stop < 0:
            pass
        self.working = False
        self.actualStop = time_h
        workTimeFromLastStart = time_h - self.actualStart
        self.totalWtLastStop += workTimeFromLastStart
        self.totalWt = self.totalWtLastStop
        self.totalBalance = self.totalWt - WT_Day.wtPlan

    def update(self, time_h):
        """
        update total hours, balance and breaks
        
        """
        if self.working:
            self.totalHours = time_h - self.start
            workTime = time_h - self.actualStart
            self.totalWt = self.totalWtLastStop + workTime
        self.totalBalance = self.totalWt - WT_Day.wtPlan
        return self.totalWt

        
        
    def endDay(self):
        """
        End of day: update stop and total hours
        
        Returns:
            todays working time
        """
        self.working = False
        self.stop = self.actualStop
        self.totalHours = self.stop - self.start
        self.totalBalance = self.totalWt - WT_Day.wtPlan
        return self.totalWt
    
    

#####################################################
class WT_Week():
    """
    Provides:
        Zeitdaten einer Woche sowie Methoden dazu
    """
    
    wtPlan = 0.
    totalWt = 0.       # total working hours excluding breaks
    totalBalance = 0.  # work time balance
    totalBreak = 0.    # break time entered by user    
    
    def __init__(self, work_time_plan=WORK_TIME_PLAN):
        WT_Week.wtPlan = work_time_plan
    
    def addDay(self, totalWt, totalBalance, totalBreak ):
        # add actual day working times
        self.totalWt += totalWt
        self.totalBalance += totalBalance
        self.totalBreak += totalBreak
    
    def checkWeekEnd(self):
        # check if week ended
        pass
    
    def update(self):
        # update week totals
        pass
        

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

class UI_():
    @classmethod
    def print(cls, txt,y=10, x=8):
        print(x,y,txt)
        _txt=str(txt)
        LCD.text(_txt,int(x),int(y),COLOR)    # x,y  from top left corner
        LCD.show()


#####################################################
    
class Config():
    """
    Provides:
        Config daten wie Soll AZ und Routinen zum lesen / schreiben
    """
    weekday = 0          # Montag ~ 0
    date = None          # date format tbd
    workTimePlan = 35.0  # planned working time per week
    breakTimeLunch = 0.5 # lunch break
    breakTimeBf = 0.25   # breakfast break
    workTimeBreak = 6.   # treshold work time to apply breakTimeBf
    configFile = 'config.json'
    
    @classmethod
    def read(cls):
        print(cls.configFile)
    
    @classmethod
    def write(cls):
        pass
    
#####################################################
class Logging():
    """
    Provides:
        Loggin of working time data per day (and per week)
    """
    
    @classmethod
    def write_day(cls):
        pass

    @classmethod
    def write_week(cls):
        pass

    
#####################################################
class MY_Time():
    TSEC_OFFSET = 0 # offset from time.time to real time-date (used in non embedded environment)
    localTimeTuple = list(time.localtime(time.time()))
    tsec = 0

    @classmethod
    def getLocaltime(cls):
        # get time data from system time (+ optional offset if not micropython)
        MY_Time.tsec = time.time() + MY_Time.TSEC_OFFSET
        lt = list(time.localtime(MY_Time.tsec))
        MY_Time.localTimeTuple = lt
        time_h = lt[3] + lt[4]/60. + lt[5]/(60.*60)   # decimal h.min_sec
        time_wd = lt[6]
        return time_h, time_wd

    @classmethod
    def changeTime(cls, time_h):   # decimal hour.min_sec
        # change time to target
        h = int(time_h)
        time_h = (time_h-h)*60
        m = int(time_h)
        time_h = (time_h-m)*60
        s = int(time_h)
        MY_Time.localTimeTuple[3:6] = (h,m,s)        
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h, time_wd

    @classmethod
    def setH0(cls,hour):
        # reset to hour start
        MY_Time.localTimeTuple[3] = int(hour)     # hour
        MY_Time.localTimeTuple[4] = 0             # minutes
        MY_Time.localTimeTuple[5] = 0             # sec
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h


    @classmethod
    def setH(cls, hour):
        # set hour, leave min:sec unchanged
        MY_Time.localTimeTuple[3] = int(hour)
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h

    @classmethod
    def setWd(cls, wd):
        # set weekday
        MY_Time.localTimeTuple[6] = int(wd)
        time_h, time_wd = MY_Time.setRTCtime()
        return time_wd

    @classmethod
    def setRTCtime(cls):
        # change rtc or adjust offset if no RTC (not embedded micropython)
        if EMBEDDED:
            machine.RTC().datetime(tuple(MY_Time.localtimeTuple))
        else:
            userAdjusted_tsec = time.mktime(tuple(MY_Time.localTimeTuple))
            tsec = time.time()
            MY_Time.TSEC_OFFSET = userAdjusted_tsec - tsec
        time_h, time_wd = MY_Time.getLocaltime()
        return time_h, time_wd

#####################################################

    
def main():
    global TIME_H, TIME_WD, TOTAL_WT, WORK_TIME_PLAN, KEY_CHR, COLOR
    print("start main")
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

#%%    
    while True:
        TIME_H, TIME_WD = MY_Time.getLocaltime()        

        if UI.query():
            KEY_CHR = ''
            key = UI.getKey()

            if   key == UI.key['start']:
                wt_day.startWork(TIME_H)
                COLOR = LCD.green

            elif key == UI.key['stop']:
                wt_day.stopWork(TIME_H)
                COLOR = LCD.red

            elif key == UI.key['resetTotal']:
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
                # set hour from user input
                if EMBEDDED:
                    pass
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
            UI.print("Last Wk Balance%d "%0,90)
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
            
        time.sleep_ms(200)
            
#######################################################
#%%
if __name__ == '__main__':     
    main()
      
