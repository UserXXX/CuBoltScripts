# The MIT License (MIT)
#
# Copyright (c) 2014 Bjoern Lange
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
Capture the flag script for cuwo.
"""


import os.path


from cuwo.script import admin
from cuwo.script import command
from cuwo.script import ServerScript
from cuwo.vector import Vector3


from states import PreGameState


from util import Flag
from util import Flagpole


SAVE_FILE = os.path.join('config', 'capture_the_flag')


KEY_FLAG_POLE_BLUE_X = 'flag_pole_blue_x'
KEY_FLAG_POLE_RED_X = 'flag_pole_red_x'
KEY_FLAG_POLE_BLUE_Y = 'flag_pole_blue_y'
KEY_FLAG_POLE_RED_Y = 'flag_pole_red_y'
KEY_FLAG_POLE_BLUE_Z = 'flag_pole_blue_z'
KEY_FLAG_POLE_RED_Z = 'flag_pole_red_z'


class CaptureTheFlagScript(ServerScript):
    def on_load(self):
        self.__load_settings()
        self.__create_flag_poles()
        self.game_state = PreGameState(self.server, self)
        
    def __load_settings(self):
        self.__settings = self.server.load_data(SAVE_FILE, {})
        if KEY_FLAG_POLE_RED_X not in self.__settings:
            self.__settings[KEY_FLAG_POLE_RED_X] = 0.0
        if KEY_FLAG_POLE_RED_Y not in self.__settings:
            self.__settings[KEY_FLAG_POLE_RED_Y] = 0.0
        if KEY_FLAG_POLE_RED_Z not in self.__settings:
            self.__settings[KEY_FLAG_POLE_RED_Z] = 0.0
        if KEY_FLAG_POLE_BLUE_X not in self.__settings:
            self.__settings[KEY_FLAG_POLE_BLUE_X] = 0.0
        if KEY_FLAG_POLE_BLUE_Y not in self.__settings:
            self.__settings[KEY_FLAG_POLE_BLUE_Y] = 0.0
        if KEY_FLAG_POLE_BLUE_Z not in self.__settings:
            self.__settings[KEY_FLAG_POLE_BLUE_Z] = 0.0
            
    def __save_settings(self):
        self.server.save_data(SAVE_FILE, self.__settings)
        
    def __create_flag_poles(self):
        s = self.server
        c = s.create_color(1.0, 0.0, 0.0, 1.0)
        self.flag_red = Flag(s, self.flag_pole_pos_red, c)
        self.flag_pole_red = Flagpole(s, self.flag_pole_pos_red, c)
        c = s.create_color(0.0, 0.0, 1.0, 1.0)
        self.flag_blue = Flag(s, self.flag_pole_pos_blue, c)
        self.flag_pole_blue = Flagpole(s, self.flag_pole_pos_blue, c)
    
    def update(self, event):
        self.game_state.update()
    
    @property
    def flag_pole_pos_red(self):
        x = self.__settings[KEY_FLAG_POLE_RED_X]
        y = self.__settings[KEY_FLAG_POLE_RED_Y]
        z = self.__settings[KEY_FLAG_POLE_RED_Z]
        return Vector3(x, y, z)
    
    @flag_pole_pos_red.setter
    def flag_pole_pos_red(self, value):
        self.__settings[KEY_FLAG_POLE_RED_X] = value.x
        self.__settings[KEY_FLAG_POLE_RED_Y] = value.y
        self.__settings[KEY_FLAG_POLE_RED_Z] = value.z
        self.flag_pole_red.pos = value
        self.__save_settings()
        
    @property
    def flag_pole_pos_blue(self):
        x = self.__settings[KEY_FLAG_POLE_BLUE_X]
        y = self.__settings[KEY_FLAG_POLE_BLUE_Y]
        z = self.__settings[KEY_FLAG_POLE_BLUE_Z]
        return Vector3(x, y, z)
    
    @flag_pole_pos_blue.setter
    def flag_pole_pos_blue(self, value):
        self.__settings[KEY_FLAG_POLE_BLUE_X] = value.x
        self.__settings[KEY_FLAG_POLE_BLUE_Y] = value.y
        self.__settings[KEY_FLAG_POLE_BLUE_Z] = value.z
        self.flag_pole_blue.pos = value
        self.__save_settings()
        
        
def get_class():
    return CaptureTheFlagScript

    
@command
@admin
def setflagpoler(script):
    player = script.get_player(None)
    if player is not None:
        ctfscript = script.server.scripts.capture_the_flag
        p = player.position
        pos = Vector3(p.x, p.y, p.z - 50000)
        ctfscript.flag_pole_pos_red = pos
        ctfscript.flag_red.pos = pos
        return 'Successful set red flag pole position.'
    else:
        return ("The command 'setflagpoler' has to be run by a "
            "player.")
            
            
@command
@admin
def setflagpoleb(script):
    player = script.get_player(None)
    if player is not None:
        ctfscript = script.server.scripts.capture_the_flag
        p = player.position
        pos = Vector3(p.x, p.y, p.z - 50000)
        ctfscript.flag_pole_pos_blue = pos
        ctfscript.flag_blue.pos = pos
        return 'Successful set blue flag pole position.'
    else:
        return ("The command 'setflagpoleb' has to be run by a "
            "player.")

@command            
def startgame(script, match_mode='autobalance'):
    ctfscript = script.server.scripts.capture_the_flag
    return ctfscript.game_state.startgame(match_mode)