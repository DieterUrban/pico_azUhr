#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 25 12:56:59 2022

worktime unit tests

@author: urban
"""
from math import isclose

from worktime import WT_Day, WT_Week, MY_Time, Config, Logging

WEEK_TIME_PLAN = 35.
BREAK_PLAN = 0.5 # 0.5

WT_Day.set_Wt_Plan(WEEK_TIME_PLAN, minBreak=BREAK_PLAN)
DAY_TIME_PLAN = WT_Day.wtPlan

#used as global variable
wt_day =  WT_Day()

# support functions to calculate work time balance in test environment
def _wt(totalWt, totalBreak=0.):
    br = max(totalBreak, BREAK_PLAN)
    work = max(0,totalWt - br)
    return work

def _balance(totalWt, totalBreak=0.):
    balance = -DAY_TIME_PLAN + _wt(totalWt, totalBreak)
    return balance

###################################################################
# unit test functions

def test_setup():
    assert isclose(WT_Day.wtPlan, WEEK_TIME_PLAN / 5)
    assert WT_Day.wtMinBreak == BREAK_PLAN


def test_wt_day():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN, time_wd = 4.)

    assert wt_day.totalHours == 0., "totalHours != 0"
    assert wt_day.totalWt == 0., "totalWt != 0"
    assert wt_day.totalBalance  == -DAY_TIME_PLAN, "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.wd == 4.,   "wd week day wrong"
    assert wt_day.working == 0 , "working wrong"

def test_startWork():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)
    wt_day.startWork(9.)

    assert wt_day.working == 2,    "working wrong"
    assert wt_day.totalHours == 0. , "totalHours wrong"
    assert wt_day.totalWt == 0., "totalWt != 0"
    assert wt_day.totalBalance  == -DAY_TIME_PLAN, "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"

    wt_day.startWork(10.)
    # 2nd start should do nothiing, values just updated according to new time_h.  0.5h break subtracted
    assert wt_day.working == 2,    "working wrong"
    assert wt_day.totalHours == 1. , "totalHours wrong"
    assert wt_day.totalWt == _wt(1.), "totalWt != 0"
    assert wt_day.totalBalance  == _balance(1.), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # unchanged, 1st start
    assert wt_day.actualStart == 9., "actualStart wrong"     # should remain unchanged

    
def test_stopWork():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)

    wt_day.startWork(9.)    
    wt_day.stopWork(10.)
    assert wt_day.working == 1,    "working wrong"
    assert wt_day.totalHours == 1. , "totalHours wrong"
    assert wt_day.totalWt == _wt(1.), "totalWt != 0"
    assert wt_day.totalBalance  == _balance(1.), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == -1., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 9., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 10., "actualStop wrong"       # last recent stop time

    wt_day.stopWork(10.5)
    assert wt_day.working == 1,    "working wrong"
    assert wt_day.totalHours == 1.5 , "totalHours wrong"
    assert wt_day.totalWt == 1., "totalWt != 0"
    assert wt_day.totalBalance  == balance(1.5, 0.5), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0.5, "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == -1., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 9., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 10., "actualStop wrong"       # last recent stop time

    
    
def test_update():
    global wt_day
    
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)
    wt_day.startWork(9.)
    wt_day.update(10.)   # 1h worked - 0.5 plan break  --> 0.5 wt
    assert wt_day.working == 2,    "working wrong"
    assert wt_day.totalHours == 1. , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(1.), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == -1., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 9., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == -1., "actualStop wrong"       # last recent stop time
    
    wt_day.update(10.5)   # 1.5h work - 0.5h plan break  --> 1.0 balance
    assert isclose(wt_day.totalHours, 1.5) , "totalHours wrong"
    assert wt_day.totalWt == _wt(1.5) , "totalWt wrong"
    assert wt_day.totalBalance  == _balance(1.5), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"

    wt_day.stopWork(10.5)  # as before
    wt_day.update(10.5)
    assert wt_day.totalHours == 1.5 , "totalHours wrong"
    assert wt_day.totalWt == _wt(1.5) , "totalWt wrong"
    assert wt_day.actualBreak  == 0., "actualBreak wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.totalBalance  == _balance(1.5), "totalBalance wrong"

    wt_day.update(11.0)    # break from stop > plan break --> full 1.5h worktime 10. -- 10.5
    assert wt_day.totalHours == 2. , "totalHours wrong"
    assert wt_day.actualBreak  == 0.5, "totalBreak wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.totalWt == _wt(2., 0.5) , "totalWt wrong"
    assert wt_day.totalBalance  == _balance(2., 0.5), "totalBalance wrong"


def test_break_calculation():
    global wt_day
    
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)
    wt_day.startWork(9.)

    wt_day.update(9.1)
    # just counting as break
    assert isclose(wt_day.totalHours, 0.1) , "totalHours wrong"
    assert isclose(wt_day.totalWt, _wt(0.1)) , "totalWt wrong"
    assert isclose(wt_day.totalBalance , _balance(0.1)), "totalBalance wrong"  # entered break time < plan break time
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"

    wt_day.update(10.)
    # plan break time exceeded --> counting work time
    assert wt_day.totalHours == 1. , "totalHours wrong"
    assert isclose(wt_day.totalWt, _wt(1.)) , "totalWt wrong"
    assert wt_day.totalBalance  == _balance(1.), "totalBalance wrong"  # entered break time < plan break time
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"

    wt_day.stopWork(10.)
    wt_day.startWork(10.1)
    # break time deducted from actual worktime is reduced even though in stop mode --> wortime icreases
    assert isclose(wt_day.totalHours, 1.1) , "totalHours wrong"
    assert isclose(wt_day.totalBreak, 0.1), "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert isclose(wt_day.totalWt, _wt(1.1, 0.1)) , "totalWt wrong"
    assert isclose(wt_day.totalBalance, _balance(1.1,0.1)), "totalBalance wrong"  # entered break time < plan break time
    
    wt_day.stopWork(10.1)
# this may cause failure ? start and stop at same time ?
    wt_day.startWork(11.0)
    # entered break > plan break -> 1h worktime expected, 1h breaktime
    assert wt_day.totalHours == 2. , "totalHours wrong"
    assert wt_day.totalBreak  == 1., "totalBreak wrong"
# this is wrong    
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
# this is wrong !
    assert isclose(wt_day.totalWt, _wt(2., 1.)) , "totalWt wrong"
    assert isclose(wt_day.totalBalance, _balance(2., 1.)), "totalBalance wrong"  # entered break time < plan break time
    

    
def test_endDay():
    global wt_day

    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)

    wt_day.startWork(9.)    
    wt_day.endDay(19.)
    assert wt_day.working == 0,    "working wrong"
    assert wt_day.totalHours == 10. , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(10.), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == 19., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 9., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 19., "actualStop wrong"       # last recent stop time
   

def test_stop_start_update_Work():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)

    wt_day.startWork(9.)    
    wt_day.stopWork(10.)
    wt_day.startWork(10.5)    
    wt_day.update(10.5)

    assert wt_day.totalHours == 1.5 , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(1.5,0.5), "totalBalance wrong"
    assert wt_day.totalBreak  == 0.5, "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == -1., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 10.5, "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 10., "actualStop wrong"       # last recent stop time


    wt_day.stopWork(18.)
    wt_day.endDay(19.)    
    wt_day.update(19.)
    wt_day.update(19.5)
    assert wt_day.working == 0,    "working wrong"
    assert wt_day.totalHours == 10. , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(+10., 0.5), "totalBalance wrong"
    assert wt_day.totalBreak  == 0.5, "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == 19., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 10.5, "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 19., "actualStop wrong"       # last recent stop time
    

def test_nstart_nstop_nupdate_Work():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)

    wt_day.startWork(9.)    
    wt_day.update(9.01)
    wt_day.startWork(9.5)    
    wt_day.update(9.51)

    wt_day.stopWork(10.)
    wt_day.update(10.01)
    wt_day.stopWork(10.5)
    wt_day.update(10.51)

    wt_day.startWork(15.)    
    wt_day.update(15.1)
    wt_day.endDay(16.0)
    wt_day.update(16.1)

    assert wt_day.totalHours == 16.-9. , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(16.-9., 15.-10.), "totalBalance wrong"
    assert wt_day.totalBreak  == 15.-10., "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == 16., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 15., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 16., "actualStop wrong"       # last recent stop time


def test_day_roll():
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)
    wt_day.startWork(9.)    
    wt_day.update(9.01)
    wt_day.endDay(19.)
    wt_day.update(19.1)
    wt_day.update(23.9)
    wt_day.update(0.01)
    
    assert wt_day.totalHours == 10. , "totalHours wrong"
    assert wt_day.totalBalance  == _balance(10.), "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"

    
def test_reset2Balance():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)

    wt_day.startWork(9.)    
    wt_day.update(9.01)
    wt_day.endDay(10.)
    wt_day.update(10.01)
    wt_day.reset2Balance(balance_today=0.)

    assert wt_day.totalHours == DAY_TIME_PLAN , "totalHours wrong"
    assert wt_day.totalBalance  == 0. , "totalBalance wrong"
    assert wt_day.totalBreak  == BREAK_PLAN, "totalBreak wrong"
    assert wt_day.firstStart == 9., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == 10., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == 9., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == 10., "actualStop wrong"       # last recent stop time
    
    
def test_getValues():
    global wt_day
    wt_day =  WT_Day(work_time_plan=WEEK_TIME_PLAN)
    wt_day.startWork(9.)    
    wt_day.update(9.01)
    wt_day.endDay(19.)
    wt_day.update(19.01)

    totalHours, totalBalance, totalBreak = wt_day.getValues()
    assert totalHours == 10. , "total Hours wrong"    
    assert totalBalance  == _balance(10.), "totalBalance wrong"
    assert totalBreak  == 0., "totalBreak wrong"


def templates():
    assert wt_day.totalHours == 0., "totalHours wrong"
    assert wt_day.totalBalance  == 0., "totalBalance wrong"
    assert wt_day.totalBreak  == 0., "totalBreak wrong"
    assert wt_day.actualBreak  == 0., "actualBreak wrong"
    
    assert wt_day.firstStart == -1., "firstStart wrong"       # todays hour.decimal first start time
    assert wt_day.finalStop == -1., "finalStop wrong"         # todays hour.decimal final stop time
    assert wt_day.actualStart == -1., "actualStart wrong"     # last recent start time (e.g. after break)
    assert wt_day.actualStop == -1., "actualStop wrong"       # last recent stop time
    assert wt_day.working == 0., "working wrong"

##############################
#%%
if False:
   print("run unit tests")
#%%
    for BREAK_PLAN in 0, 0.5:
        WT_Day.set_Wt_Plan(WEEK_TIME_PLAN, minBreak=BREAK_PLAN)
        DAY_TIME_PLAN = WT_Day.wtPlan
        test_setup()
        test_wt_day()
        test_startWork()
        test_stopWork()
        test_update()
        test_endDay()
        test_break_calculation()
        test_stop_start_update_Work()
        test_nstart_nstop_nupdate_Work() 
        test_day_roll()
        test_reset2Balance()
        test_getValues()


# = error cases