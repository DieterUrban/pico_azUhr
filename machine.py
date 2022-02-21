#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 18:04:48 2022

Dummy machine library for debugging with python
(e.g. for LCD simulation)

provides dummy routines for
from machine import Pin,SPI,PWM

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
        self.nr = args[0]
        self.out = args[1] if len(args) > 1 else 0
        # add here mapping to key presses
    
    def write(self, *args, **karargs):
        pass
    
    def value(self):
        return 1
        # add to return 0 if key pressed    
    
    
    # brauche direkte instance call: pin(1)  wenn pin=Pin()
    def __call__(self, *args, **kwargs):
        pass

class PWM():
        
        def __init__(self,*args, **kwargs):
            pass
    
        def freq(self,*args,**kwargs):
            pass

        def duty_u16(self,*args,**kwargs):
            pass
        

