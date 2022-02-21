#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 21 18:04:48 2022

Dummy framebuff library for debugging with python
(e.g. for LCD simulation)

provides dummy routines for
framebuf

@author: urban
"""


# (framebuf.FrameBuffer)

RGB565=None

black = 0
red = 1
green = 2
blue = 4
white = 15

class FrameBuffer():

    
    def __init__(self,*args, **kwargs):
        pass
    
    def fill(self, *args, **karargs):
        pass

    def fill_rect(self, x1,y1,x2,y2,color, *args, **karargs):
        pass

    def rect(self, x1,y1,x2,y2,color, *args, **karargs):
        pass


    def line(self, x1,y1,x2,y2,color, *args, **karargs):
            print((x1,y1),(x2,y2),color)

    def text(self, txt, x, y, color, *args, **karargs):
        print(txt)

    def show(self, *args, **karargs):
        pass



    
