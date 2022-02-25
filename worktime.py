#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 11:04:13 2022

@author: urban

Zeiterfassung bzw. fkt zur Berechnung

AZ-Model:
    0.5h Pause täglich abgezogen. Wenn AZ-pause --> darin berücksichtigen
    wenn AZ > 6h --> weitere 0.25h Abzug.   AZ-pausen ebenfalls berücksichtigen


time handling routines in MY_Time
adapts between micropython  and python differences
(eg. RTC function and different time.localtime)

micropython localtime 
    (year, month, mday, hour, minute, second, weekday, yearday)
RTC.datetime:
    (year, month, day, weekday, hours, minutes, seconds, subseconds)
RTC.init:
(year, month, day[, hour[, minute[, second[, microsecond[, tzinfo]]]]])    

"""
import time
import json

EMBEDDED = True
WORK_TIME_PLAN = 35.0 # default work time per hour plan

#####################################################

class WT_Day():
    """
    Provides:
        Zeitdaten eines Tages sowie Methoden rund um Zeiteinträge
    """
    wtPlan = 0.        # work time per day plan
    wtMinBreak = 0.    # min break according to plan
    
    @classmethod
    def set_Wt_Plan(cls, work_time_plan, minBreak=None):
        WT_Day.wtPlan = round(work_time_plan/5.,2)
        if minBreak:
            WT_Day.wtMinBreak = minBreak

    def __init__(self, 
                       work_time_plan=WORK_TIME_PLAN,
                       time_wd=0
                       ):
        self.wd = time_wd          # week day (0 = Monday). not used (and not updated) internaly  
        WT_Day.set_Wt_Plan(work_time_plan)
        # values set by work status change events
        self.firstStart = -1       # todays hour.decimal first start time
        self.finalStop = -1        # todays hour.decimal final stop time
        self.actualStart = -1      # last recent start time (e.g. after break)
        self.actualStop = -1       # last recent stop time
        # self.totalWtLastStop = 0.  # total working hours excluding breaks up to last stop
        self.totalBreak = 0.       # break time entered by user  (with actualBreak time )
        # these values get regular update
        self.totalWt = 0.          # total working hours -breaks up to actual time
        self.totalBalance = -WT_Day.wtPlan   # work time balance (totalWt - plan) up to actual time. wtMinBreak subtracted
        self.totalHours = 0.       # total time actual or stop - start
        self.actualBreak = 0.      # duration of actual break
        self.working = 0           # working (2) or break (1) or endOfWork (0) status
    
    def startWork(self, time_h):
        """
        Set start work timestamp. 
        If not first --> end break and update break time
        """
        # status to working
        if self.firstStart < 0:
            self.firstStart = time_h
        if self.actualStop >= 0 and self.working == 1:
            # ending a break -> update break time
            actualBreak = time_h - self.actualStop
            self.totalBreak += actualBreak
        if self.working < 2:
            self.actualStart = time_h
        self.actualBreak = 0
        self.working = 2
        self.update(time_h)
        
    
    def stopWork(self, time_h):
        """
        Set stop work timestamp. 
        Update totalWT = total Worktime
        """
        if self.firstStart < 0:
            # stop before start ... do nothing
            return
        if self.finalStop >= 0:
            # restart from dayEnd, is ok
            pass
        if self.working > 1:
            # new stop 
            self.actualStop = time_h
            #workTimeFromLastStart = time_h - self.actualStart
            #self.totalWtLastStop += workTimeFromLastStart
        self.working = 1
        #self.totalWt = self.totalWtLastStop
        #self.totalBalance = self.totalWt - WT_Day.wtPlan
        self.update(time_h)


    def update(self, time_h):
        """
        update total hours, balance and breaks
        
        """
        if self.working >= 2:
            # working status
            self.totalHours = time_h - self.firstStart
            #newWorkTime = time_h - self.actualStart     # wortime since last break end
            #self.totalWt = self.totalWtLastStop + newWorkTime
            self.totalWt = self._totalWt()
        elif self.working == 1:
            # break status
            self.totalHours = time_h - self.firstStart
            self.actualBreak = time_h - self.actualStop
            self.totalWt = self._totalWt()
        else:
            # endDay status
            pass
        self.totalBalance = self._totalBalance()
        return self.totalWt


    # update according to provided balance: used after restart. Assuming to be in endDay status
    def reset2Balance(self, balance_today):
        hours = balance_today + WT_Day.wtPlan
        self.totalHours = hours
        self.totalBalance = balance_today
        # self.totalWtLastStop = hours
        self.totalBreak = WT_Day.wtMinBreak
        # leave update of some internal values to next update call
        #self.totalWt = hours
        
        
    def endDay(self, time_h=None):
        """
        End of day: update stop and total hours
        
        Returns:
            todays working time
        """
        # status to end of Day (= no break, no working)
        self.working = 0
        if time_h:
            # use as stop time
            self.actualStop = time_h
        self.finalStop = self.actualStop
        self.totalHours = self.finalStop - self.firstStart
        self.totalWt = self._totalWt()
        self.totalBalance =  self._totalBalance()
        if time_h: self.update(time_h)
        return self.totalWt
    
    def getValues(self):
        return (self.totalHours, self.totalBalance, self.totalBreak+self.actualBreak)
    
    
    def _totalWt(self):
        breaks = max(self.totalBreak+self.actualBreak, WT_Day.wtMinBreak)
        return max(0.,self.totalHours - breaks)
    
    def _totalBalance(self):
        return self.totalWt - WT_Day.wtPlan
        
#####################################################

class WT_Week():
    """
    Provides:
        Zeitdaten einer Woche sowie Methoden dazu
    """
    
    wtPlan = WORK_TIME_PLAN   # default
        
    def __init__(self, work_time_plan=WORK_TIME_PLAN):
        WT_Week.wtPlan = work_time_plan
        self.totalWt = 0.                 # week total, including today (partial today)
        self.totalBalance = -WT_Week.wtPlan
        self.totalBreak = 0.
        self.totalWt_notToday = 0.        # sum up to last day
        self.totalBalance_notToday = -(WT_Week.wtPlan*4/5)
        self.totalBreak_notToday = 0.

    # final  update for a day, to be executed after work end !
    def addDay(self, totalWt, totalBalance, totalBreak ):
        # add actual day working times
        self.totalWt_notToday = self.totalWt
        self.totalWt = self.totalWt_notToday + totalWt
        self.totalBalance_notToday = self.totalBalance
        self.totalBalance = self.totalBalance_notToday + totalBalance
        self.totalBreak_notToday = self.totalBreak
        self.totalBreak = self.totalBreak_notToday + totalBreak
    
    def checkWeekEnd(self):
        # check if week ended
        # e.g. check if no keypress for > 12h  or if > 1 day idle ...
        pass
    
    # running update for actual day
    def update(self,totalWt, totalBalance, totalBreak):
        self.totalWt = self.totalWt_notToday + totalWt
        self.totalBalance = self.totalBalance_notToday + totalBalance
        self.totalBreak = self.totalBreak_notToday + totalBreak

    def getValues(self):
        return (self.totalWt, self.totalBalance, self.totalBreak)
        

#####################################################

class Config():
    """
    Provides:
        Config daten wie Soll AZ und Routinen zum lesen / schreiben
    """
    config = {
        # values to support restart after power break
        'date': (2020,1,1),       # actual date tuple (year,month,date)
        'time':    0.0,           # actual time in decimal format  23.999
        'balance_today':    0.,   # balance time actual day
        'balance_past': 0.,       # balance accumulated from old days 
         # config values, not changed by program
        'workTimePlan':   39.0,   # planned working time per week
        'breakTime': 0.5          # minimum (lunch) break time per day
    }
    configFile = 'config.json'    # without directory works on both embedded and non embedded
    
    @classmethod
    def read(cls):
        file = Config.configFile
        try:
            with open(file, 'r') as f:
                Config.config = json.load(f)
                f.close()
        except:
            # create new file if not exists
            Config.write()
        return Config.config
                
    @classmethod
    def write(cls):
        file = Config.configFile
        with open(file, 'w') as f:
            f.write(json.dumps(Config.config))
            f.flush()
            f.close()
            print("config written")
            return True
        return False
    
    @classmethod
    def setToday(cls, time=None, hours_today=None, date=None, balance_past=None):
        if time:
            Config.config['time'] = time
        if hours_today:
            Config.config['hours_today'] = hours_today
        if date:
            Config.config['date'] = date
        if balance_past:
            Config.config['balance_past'] = balance_past
        return Config.config    

    # update full actual state
    @classmethod
    def updateState(cls, wt_day=None, time=None, date=None):
        if time:
            Config.config['time'] = time
        if date:
            Config.config['date'] = date
        if wt_day:
            Config.config['balance_today'] = wt_day.totalBalance
            #CONFIG.config['balance_past'] = 0.
        return Config.config    
                


#import json
#f.write(ujson.dumps(config))
#c = ujson.loads(f.readall())
 
    
#####################################################
class Logging():
    """
    Provides:
        Loggin of working time data per day (and per week)
    """
        
    @classmethod
    def write_day(cls, time, values):    # time = timeTuple, list of values
        file = 'logDay.csv'
        time_txt = '.'.join([str(x) for x in time[2:0:-1]])+'.'
        line = ', '.join([str(x) for x in values]) + '\n'
        with open(file, 'a') as f:
            f.write(time_txt+', '+line)
            f.flush()
            f.close()
            return True
        return False
        

    @classmethod
    def write_week(cls, time, values):
        file = 'logWeek.csv'
        time_txt = '.'.join([str(x) for x in time[2:0:-1]])+'.' 
        line = ', '.join([str(x) for x in values]) + '\n'
        with open(file, 'a') as f:
            f.write(time_txt+', '+line)
            f.flush()
            f.close()
            return True
        return False
    

#####################################################
class MY_Time():
    """
    Provides:
        Fkt zur Teitberechnung und Einsetllung
    """
    
    TSEC_OFFSET = 0 # offset from time.time to real time-date (used in non embedded environment)
    localTimeTuple = list(time.localtime(time.time()))
    tsec = 0
    RTC = None   # to be set to machine.RTC, will use RTC.datetime() Function which is machine.RTC.datetime in micropython

    @classmethod
    def getLocaltime(cls):
        # get time data from system time (+ optional offset if not micropython)
        MY_Time.tsec = time.time() + MY_Time.TSEC_OFFSET
        lt = list(time.localtime(MY_Time.tsec))
        MY_Time.localTimeTuple = lt
        time_h = lt[3] + lt[4]/60. + lt[5]/(60.*60)   # decimal h.min_sec
        time_wd = lt[6]
        return time_h, time_wd

    # convert decimal hour.min_sec to 3x int 
    # negative values result in negative hh, min and sec. are as positives (for use in -hh:mm:ss print)
    @classmethod
    def convert2hms(cls, time_h): 
        # change time to target
        h = int(time_h)
        time_h = abs((time_h-h)*60)
        m = int(time_h)
        time_h = (time_h-m)*60
        s = int(time_h)
        return (h,m,s)

    # set localTime to new value from decimat time  
    @classmethod
    def setTime(cls, time_h):   # decimal hour.min_sec
        h,m,s = MY_Time.convert2hms(time_h)
        MY_Time.localTimeTuple[3:6] = (h,m,s)        
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h, time_wd

    # set localTime to new full hour
    @classmethod
    def setH0(cls,hour):
        # reset to hour start
        MY_Time.localTimeTuple[3] = int(hour)     # hour
        MY_Time.localTimeTuple[4] = 0             # minutes
        MY_Time.localTimeTuple[5] = 0             # sec
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h

    # set localTime hour without changing minutes / seconds
    @classmethod
    def setH(cls, hour):
        # set hour, leave min:sec unchanged
        MY_Time.localTimeTuple[3] = int(hour)
        time_h, time_wd = MY_Time.setRTCtime()
        return time_h

    # set date from tuple year,month,day  
    @classmethod
    def setDate(cls, date_tuple):
        print("setDate", date_tuple)
        MY_Time.localTimeTuple[0:3] = [int(x) for x in date_tuple]
        time_h, time_wd = MY_Time.setRTCtime()
        return time_wd

    # set weekday by adjusting date. works for small adjustments +/- 1
    @classmethod
    def changeDate(cls, delta=0):    # delta days
        # set weekday by adjusting date
        month, day = MY_Time.localTimeTuple[1:3]
        day += delta
        if day < 0:
            day = 30
            month -= 1
        if day > 30:
            day = 1
            month += 1
        MY_Time.localTimeTuple[1] = month
        MY_Time.localTimeTuple[2] = day        
        time_h, time_wd = MY_Time.setRTCtime()
        return time_wd

    @classmethod
    def setRTCtime(cls):
        # change rtc or adjust offset if no RTC (not embedded micropython)
        if EMBEDDED:
            #  localtime is    (year, month, mday, hour, minute, second, weekday, yearday)
            #  RTC.init uses   (year, month, day[, hour[, minute[, second[, microsecond[, tzinfo]]]]])  but not availabe with pico !
            #  RTC.datetime    (year, month, day, weekday, hours, minutes, seconds, subseconds)
            tt = list(MY_Time.localTimeTuple)
            MY_Time.RTC.datetime(tt[0:3] + tt[6:7] + tt[3:6] + [0])
        else:
            userAdjusted_tsec = time.mktime(tuple(MY_Time.localTimeTuple))
            tsec = time.time()
            MY_Time.TSEC_OFFSET = userAdjusted_tsec - tsec
        time_h, time_wd = MY_Time.getLocaltime()
        print("setRTCTime", time_wd, time_h)
        return time_h, time_wd
    
       
#######################################################
#%%
if False:
    # unit tests
    
    MY_Time.RTC = machine.RTC()
    
    config = Config()

    Config.read()
    
    WORK_TIME_PLAN = Config.workTimePlan
    KEY_CHR = ''
    dayEndProcessed = False
    
      
