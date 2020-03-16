'''
CircuitPython DJ
Inspired by LSDJ and nanoloop gameboy trackers
Code snippets and libraries from the following Adafruit Learning Guides:
    FruitBox Sequencer
    PyBadge GamePad
    Feather Waveform Generator in CircuitPython
    Circuit Playground Express USB MIDI Controller and Synthesizer

'''


import time
import array
import math
import digitalio
import board
import busio
import neopixel
import displayio
import simpleio
import terminalio
import audioio
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_text import label
from digitalio import DigitalInOut, Direction, Pull
from adafruit_bus_device.i2c_device import I2CDevice
from gamepadshift import GamePadShift
from micropython import const
from analogio import AnalogOut
from generator import Generator
import shapes
import pitches
from notevals import display_note

import usb_midi

import adafruit_lis3dh
import adafruit_midi

from adafruit_midi.note_on          import NoteOn
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.pitch_bend       import PitchBend

from adafruit_midi.note_on          import NoteOn
from adafruit_midi.control_change   import ControlChange
from adafruit_midi.pitch_bend       import PitchBend


midi_note_C4 = 60
midi_cc_modwheel = 1  # was const(1)

velocity = 127
min_octave = -3
max_octave = +3
octave = 0
min_semitone = -11
max_semitone = +11
semitone = 0


# Button Constants
BUTTON_LEFT = const(128)
BUTTON_UP = const(64)
BUTTON_DOWN = const(32)
BUTTON_RIGHT = const(16)
BUTTON_SEL = const(8)
BUTTON_START = const(4)
BUTTON_A = const(2)
BUTTON_B = const(1)

pad = GamePadShift(digitalio.DigitalInOut(board.BUTTON_CLOCK),
                   digitalio.DigitalInOut(board.BUTTON_OUT),
                   digitalio.DigitalInOut(board.BUTTON_LATCH))


speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.direction = digitalio.Direction.OUTPUT
speaker_enable.value = False


midi_channel = 1
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1],
                          out_channel=midi_channel-1)





bpm = 60  # quarter note beats per minute
beat = 15 / bpm  # 16th note expressed as seconds, each beat is this long

seq = [] * 16   #16 step sequence


def customwait(wait_time):
        start = time.monotonic()
        while time.monotonic() < (start + wait_time):
            pass

def sequencer(seq, beat, gridbeat, x):
    # I have a feeling that each step needs to be iterated indiviually in the running loop
    beatstep = x
    #gridbeat = Rect( (52), (5), 24, 24, outline=0xF00000, stroke=3)

    beatstep = selection_update('right',beatstep, gridbeat)
    if seq[x] == 0:
        customwait(beat)
    else:
        midi.send(NoteOn(seq[x], 127))
        customwait(beat)
        midi.send(NoteOn(seq[x], 0))
    

def selection_update(dir,current, type):
    if dir == 'left':
        if current % 4 != 0:     #0, 4, 8, 12
            type.x = type.x - 24
            current -= 1
            return current
        elif current == 0:
            return current
        else:
            type.x = type.x + 24 * 3
            type.y = type.y - 24
            current -= 1
            return current
    if dir == 'right':
        if current % 4 != 3:     #3, 7, 11, 15
            type.x = type.x + 24
            current += 1
            return current
        elif current == 15:
            type.x = 52
            type.y = 5
            current = 0
            return current
        else:
            type.x = type.x - 24 * 3
            type.y = type.y + 24
            current += 1
            return current
    if dir == 'up':
        if current > 3 :     #3, 7, 11, 15
            type.y = type.y - 24
            current -= 4
            return current
        elif current < 4:
            return current
        else:
            type.x = type.x - 24 * 3
            type.y = type.y + 24
            current += 1
            return current
    if dir == 'down':
        if current < 12:     #3, 7, 11, 15
            type.y = type.y + 24
            current += 4
            return current
        elif current > 11:
            return current
        else:
            type.x = type.x - 24 * 3
            type.y = type.y + 24
            current += 1
            return current

    



speaker_enable.value = False
# We are going to send midi to another board or out over usb in this project

display = board.DISPLAY

# Set text, font, and color
text = "ChrisLeeWoo"
font = terminalio.FONT
color = 0x0000FF

# Create the text label
text_area = label.Label(font, text="ChrisLeeWoo", color=0x6F9FAF)

# Set the location
text_area.x = 23
text_area.y = 23

# Show it
# display.show(text_area)

# Make the display context
splash = displayio.Group(max_size=10)
display.show(splash)

# Make a background color fill
color_bitmap = displayio.Bitmap(160, 128, 1)
color_palette = displayio.Palette(1)
#color_palette[0] = 0x000000
bg_sprite = displayio.TileGrid(color_bitmap, x=20, y=20,
                               pixel_shader=color_palette)
splash.append(bg_sprite)
##########################################################################

# add my sprite

roundrect = RoundRect(10, 10, 90, 30, 10, fill=0x0, outline=0xAFAF00, stroke=6)
splash.append(roundrect)
splash.append(text_area)
# insert play startup sound here ######
customwait(1)

mixgrid = displayio.Group(max_size=64)
    

for m in range(64):
    blankness = label.Label(font, text="   ", color=0xff9Fff)
    mixgrid.append(blankness)

screen_rects = -1

for g in range(4):
        for h in range(4):
            screen_rects += 1
            gridsq = Rect( (52+24*g), (5+24*h), 24, 24, fill=0x0, outline=0xAFAFFF, stroke=2)
            mixgrid.pop(screen_rects)
            mixgrid.insert( (screen_rects) , gridsq)


# mixgrid values 0 to 15
display.show(mixgrid)



pixel_pin = board.D8
num_pixels = 8

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def color_chase(color, wait):
    for i in range(num_pixels):
        pixels[i] = color
        time.sleep(wait)
        pixels.show()
    customwait(0.5)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(rc_index & 255)
        pixels.show()
        customwait(wait)








def set_grid_disp(note,spot):
    #be aware of overwriting a current note
    # this changes the text in the box
    # clear the screen starting at (54,7) with size 20

    mixgrid.pop(spot+16)
    thing = label.Label(font, text=note, color=0xff9Fff)
    thing.x = pixelocate_x(spot)
    thing.y = pixelocate_y(spot)
    #insert(index, layer)
    mixgrid.insert(spot+16, thing)

def set_note_playing(note,spot):
    # eventually I want it to display the note name, not just the midi note number
    # mixgrid 34 
    
    mixgrid.pop(34)
    noteval = label.Label(font, text=display_note(note), color=0xff9Fff)  #initialize text in each box
    noteval.x = 5
    noteval.y = 112
    mixgrid.insert(34, noteval)
    #mixgrid.insert(32, noteval)



def pixelocate_x(number):
    return 55 + 24 * ( number % 4 )

def pixelocate_y(number):
    if number < 4:
        return 15
    elif number < 8:
        return 15 + 24
    elif number < 12:
        return 15 + 24*2
    else: return 15 + 24*3




RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
OFF = (0,0,0)
PLAY = (0,10,0)
current_buttons = pad.get_pressed()
last_read = 0

for g in range(16):
    g0 = label.Label(font, text="   ", color=0xff9Fff)  #initialize text in each box
    mixgrid.pop(g+16)
    mixgrid.insert(g+16,g0)
    # mixgrid values 16 to 31

#set_grid_disp('c#4',14)
#time.sleep(.5)
#set_grid_disp('   ',14)
#time.sleep(.5)
#set_grid_disp('a 7',14)
#time.sleep(.1)
#set_grid_disp('c 5',14)

selection = Rect( (52), (5), 24, 24, outline=0xFFAA00, stroke=3)
mixgrid.pop(32)
mixgrid.insert(32,selection)
selected = 0
# mixgrid 32

gridbeat = Rect( (52), (5), 24, 24, outline=0xF00000, stroke=2)
mixgrid.pop(33)
mixgrid.insert(33, gridbeat)
#mixgrid 33

print("playing")

print (display_note(10))
x = 0
seq = [10, 20, 0, 40, 50, 60, 70, 80, 0, 20, 30, 40, 50, 60, 70, 80]
#sequencer (seq, beat, gridbeat, x)

for step in range(16):
    # we are setting up an initial sequence in this demo program
    set_grid_disp(display_note(seq[step]), step)



print("stopped")
playing = False


while True:

    #x = 0
    #y = 0
    #z = 0
    #COLOR = (x,y,z)
    #for v in range (5):
    #    x = v+1 % 255
    #    y = v+1 % 255
    #    z = v+1 % 255
    #COLOR = (x,y,z)
    #pixels.fill(OFF)
    #pixels.show()

    if playing:
        gridbeat.outline = 0x009900
        sequencer (seq, beat, gridbeat, x)
        x = (x+1) % 16
        pixels.fill(PLAY)
        pixels.show()
        set_note_playing((seq[x]),0)

    else:
        pixels.fill(OFF)
        pixels.show()

            # Reading buttons too fast returns 0
    if (last_read + 0.1) < time.monotonic():
        buttons = pad.get_pressed()
        last_read = time.monotonic()
    if current_buttons != buttons:
        # Respond to the buttons
        if (buttons == BUTTON_SEL + BUTTON_A): #
            customwait(.1)
        elif (buttons == 0b01000100):
            customwait(.1)

        elif (buttons == 0b10000100):
            customwait(.1)

        elif (buttons & BUTTON_LEFT) > 0:
            selected = selection_update('left', selected, selection)
            print('Left', selected)

        elif (buttons & BUTTON_RIGHT) > 0:
            selected = selection_update('right', selected, selection)
            print('Right', selected)

        elif (buttons & BUTTON_UP) > 0 :
            selected = selection_update('up', selected, selection)
            print('Up', selected)
            #print('Up', buttons)
        elif (buttons & BUTTON_DOWN) > 0 :
            selected = selection_update('down', selected, selection)
            print('Down', selected)
        elif (buttons & BUTTON_A) > 0 :
            print('A', buttons)
        elif (buttons & BUTTON_B) > 0 :
            print('B', buttons)
        elif (buttons & BUTTON_START) > 0 :
            if playing == False:
                playing = True
            else:
                playing = False
            print('Start', buttons)

        elif (buttons & BUTTON_SEL) > 0 :
            print('Select', buttons)



        current_buttons = buttons
