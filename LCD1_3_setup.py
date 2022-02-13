"""
Waveshare 1.3 " Display + switches/Joystick setup
https://www.waveshare.com/wiki/Pico-LCD-1.3

"""


from machine import Pin,SPI,PWM
from Pico_LCD1_3 import LCD_1inch3
import framebuf

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

KEYA = Pin(15,Pin.IN,Pin.PULL_UP)     # right top
KEYB = Pin(17,Pin.IN,Pin.PULL_UP)     # right 2nd from top
KEYX = Pin(19 ,Pin.IN,Pin.PULL_UP)    # right 3rd from top
KEYY= Pin(21 ,Pin.IN,Pin.PULL_UP)     # right bottom

UP = Pin(2,Pin.IN,Pin.PULL_UP)        # joystick 
DOWN = Pin(18,Pin.IN,Pin.PULL_UP)
LEFT = Pin(16,Pin.IN,Pin.PULL_UP)
RIGHT = Pin(20,Pin.IN,Pin.PULL_UP)
CTRL = Pin(3,Pin.IN,Pin.PULL_UP)      # press joystick
