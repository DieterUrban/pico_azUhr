#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 11:04:13 2022

@author: urban

Zeiterfassung bzw. fkt zur Berechnung

AZ-Model:
    0.5h Pause täglich abgezogen. Wenn AZ-pause --> darin berücksichtigen
    wenn AZ > 6h --> weitere 0.25h Abzug.   AZ-pausen ebenfalls berücksichtigen

"""
import time

EMBEDDED = True
WORK_TIME_PLAN = 35.0 # default work time per hour plan

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
        self.totalBalance = 0.
        self.totalHours = 0.
        self.totalWt = 0.
        self.totalBreak = 0.
        WT_Day.set_Wt_Plan(work_time_plan)
        self.wd = time_wd    # week day    
        self.start = -1
        self.stop = -1
        self.actualStart = -1
        self.actualStop = -1
    
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
    
    def getValues(self):
        return (self.totalHours, self.totalBalance, self.totalBreak)
        
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

    @classmethod
    def changeTime(cls, time_h):   # decimal hour.min_sec
        h,m,s = MY_Time.convert2hms(time_h)
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
        if False and  EMBEDDED:
            MY_Time.RTC.datetime(tuple(MY_Time.localTimeTuple))    # does not work on picco ! ???
        else:
            userAdjusted_tsec = time.mktime(tuple(MY_Time.localTimeTuple))
            tsec = time.time()
            MY_Time.TSEC_OFFSET = userAdjusted_tsec - tsec
        time_h, time_wd = MY_Time.getLocaltime()
        return time_h, time_wd

#####################################################

    
       
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
    
      
