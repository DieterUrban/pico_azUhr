#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 18:04:48 2022

Dummy machine and framebuff for LCD simulation

provides dummy routines for
from machine import Pin,SPI,PWM
import framebuf

@author: urban
"""



class SPI():
    
    def __init__(self,*args, **kwargs):
        pass
    
    def write(self, *args, **karargs):
        pass
    
    
class Pin():
    OUT = 1
    IN = 0
    PULL_UP = 0
    
    def __init__(self,*args, **kwargs):
        pass
    
    def write(self, *args, **karargs):
        pass
    
    # brauche pin(1)  wenn pin=Pin()
    

class PWM():
        
        def __init__(self,*args, **kwargs):
            pass
    
        def freq(self,*args,**kwargs):
            pass

        def duy_u16(self,*args,**kwargs):
            pass
        

