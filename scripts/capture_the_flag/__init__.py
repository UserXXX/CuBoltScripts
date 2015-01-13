# The MIT License (MIT)
#
# Copyright (c) 2014-2015 Bjoern Lange
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


"""Capture the flag script for cuwo."""


import math
import os.path
import shutil
from datetime import datetime


from cuwo import static


from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.constants import HOSTILE_TYPE
from cuwo.constants import FRIENDLY_TYPE
from cuwo.script import admin
from cuwo.script import command
from cuwo.script import ConnectionScript
from cuwo.script import ServerScript
from cuwo.vector import Vector3


from .states import PreGameState
from .states import GameRunningState


from .loot import LootManager


from .util import Flag
from .util import Flagpole


# Path to save and config file
SAVE_FILE = 'capture_the_flag'
DEFAULT_CONFIG_FILE = 'scripts/capture_the_flag/default_config.py'
CONFIG_FILE = 'config/capture_the_flag.py'


# Keys used in settings dict
KEY_FLAG_POLE_BLUE_X = 'flag_pole_blue_x'
KEY_FLAG_POLE_RED_X = 'flag_pole_red_x'
KEY_FLAG_POLE_BLUE_Y = 'flag_pole_blue_y'
KEY_FLAG_POLE_RED_Y = 'flag_pole_red_y'
KEY_FLAG_POLE_BLUE_Z = 'flag_pole_blue_z'
KEY_FLAG_POLE_RED_Z = 'flag_pole_red_z'


# Movement speed cap and min update time
MOVEMENT_SPEED_CAP = 7500000
MOVEMENT_SPEED_FPS = 1 / 60


from .constants import RELATION_FRIENDLY_PLAYER
from .constants import RELATION_FRIENDLY
from .constants import RELATION_HOSTILE_PLAYER
from .constants import RELATION_HOSTILE
from .constants import RELATION_NEUTRAL


STRING_RELATION_MAPPING = {
    'friendly_player' : RELATION_FRIENDLY_PLAYER,
    'friendly' : RELATION_FRIENDLY,
    'hostile_player' : RELATION_HOSTILE_PLAYER,
    'hostile' : RELATION_HOSTILE,
    'neutral' : RELATION_NEUTRAL
}


class CaptureTheFlagConnectionScript(ConnectionScript):
    """ConnectionScript handling a single players connection."""
    def __init__(self, parent, connection):
        self.__joined = False
        self.__last_hp = 0
        return super().__init__(parent, connection)

    def on_entity_update(self, event):
        """Handles cuwo's on_entity_update event.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        if not self.__joined:
            self.__joined = True
            self.parent.game_state.player_join(self.connection)
            self.__last_hp = self.entity.hp
            self.old_pos = self.entity.pos
            self.old_time = datetime.now()
        else:
            if self.__last_hp <= 0 and self.entity.hp > 0:
                self.parent.game_state.on_respawn(self.entity)
            self.__last_hp = self.entity.hp
    
    def on_unload(self):
        """Handles cuwo's on_unload event."""
        self.parent.game_state.on_leave()
        self.parent.game_state.player_leave(self.connection)
        
    def on_hit(self, event):
        """Handles cuwo's on_hit event.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        self.parent.game_state.on_hit(self.connection, event.target)
        
    def on_kill(self, event):
        """Handles cuwo's on_kill event.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        target_id = event.target.entity_id
        xp_on_kill = self.server.config.capture_the_flag.xp_on_kill
        if xp_on_kill and target_id in self.server.players:
            entity = self.connection.entity
            self.parent.game_state.on_kill(entity, event.target)
            
    def on_pos_update(self, event):
        """Handles a position update of this player.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        if self.server.config.capture_the_flag.speed_cap:
            t = datetime.now()
            pos = self.entity.pos
            x = self.old_pos.x - pos.x
            y = self.old_pos.y - pos.y
            z = self.old_pos.z - pos.z
            dif = math.sqrt(x*x + y*y + z*z)
            elapsed = (t - self.old_time).total_seconds()
            if elapsed > MOVEMENT_SPEED_FPS:
                average_speed = dif / elapsed
                if average_speed > MOVEMENT_SPEED_CAP:
                    self.parent.game_state.too_fast(self.connection)
                self.old_pos = pos
                self.old_time = t
            
    def init_game(self):
        """Initializes this player for a new game."""
        self.old_time = datetime.now()
        self.old_pos = self.connection.entity.pos


class CaptureTheFlagScript(ServerScript):
    """ServerScript managing CTF."""
    connection_class = CaptureTheFlagConnectionScript

    def on_load(self):
        """Handles the loading of this script."""
        self.__load_settings()
        self.loot_manager = LootManager(self.server)
        self.load_config()
        self.__create_flag_poles()
        self.game_state = PreGameState(self.server, self)
        
    def on_unload(self):
        """Handles the unloading of this script."""
        try:
            self.flag_pole_red.dispose()
            self.flag_pole_blue.dispose()
        except AttributeError:
            pass
        
    def __load_settings(self):
        """Loads the settings from disk and sets default values if
        not contained.
        
        """
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
                
    def load_config(self):
        """Loads the config from disk and creates a default file if
        none exists.
        
        """
        try:
            self.server.config.capture_the_flag
        except KeyError:
            shutil.copyfile(DEFAULT_CONFIG_FILE, CONFIG_FILE)
            self.server.config.capture_the_flag

        r = self.server.config.capture_the_flag.relation_between_matches
        for p1 in self.server.players.values():
            for p2 in self.server.players.values():
                p1.entity.set_relation_to(p2.entity, r)
           
    def apply_config(self):
        """Applies the current config. Called after reloading
        config.
        
        """
        config = self.server.config
        relation = config.capture_the_flag.relation_between_matches
        for p1 in self.server.players:
            for p2 in self.server.players:
                p1.entity.set_relation_to(p2.entity, relation)
            
    def __save_settings(self):
        """Saves the settings to disk."""
        # make sure save directory exists
        if not os.path.exists('./save'):
            os.makedirs('./save')
        self.server.save_data(SAVE_FILE, self.__settings)
        
    def __create_flag_poles(self):
        """Initializes the flag poles."""
        s = self.server
        c = (1.0, 0.0, 0.0, 1.0)
        self.flag_red = Flag(s, self.flag_pole_pos_red, c, 'red')
        self.flag_pole_red = Flagpole(s, self.flag_pole_pos_red, c)
        c = (0.0, 0.0, 1.0, 1.0)
        self.flag_blue = Flag(s, self.flag_pole_pos_blue, c, 'blue')
        self.flag_pole_blue = Flagpole(s, self.flag_pole_pos_blue, c)
    
    def update(self, event):
        """Updates the script."""
        self.game_state.update()
        
    def get_mode(self, event):
        """Returns the mode the server is running in.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        return 'CTF'
    
    @property
    def flag_pole_pos_red(self):
        """Returns the red flag poles position.
        
        Return value:
        The position of the red flag pole as a Vector3
        
        """
        x = self.__settings[KEY_FLAG_POLE_RED_X]
        y = self.__settings[KEY_FLAG_POLE_RED_Y]
        z = self.__settings[KEY_FLAG_POLE_RED_Z]
        return Vector3(x, y, z)
    
    @flag_pole_pos_red.setter
    def flag_pole_pos_red(self, value):
        """Sets the position of the red flag pole.
        
        Keyword arguments:
        value -- Value to set the position to
        
        """
        self.__settings[KEY_FLAG_POLE_RED_X] = value.x
        self.__settings[KEY_FLAG_POLE_RED_Y] = value.y
        self.__settings[KEY_FLAG_POLE_RED_Z] = value.z
        self.flag_pole_red.pos = value
        self.__save_settings()
        
    @property
    def flag_pole_pos_blue(self):
        """Returns the blue flag poles position.
        
        Return value:
        The position of the blue flag pole as a Vector3
        
        """
        x = self.__settings[KEY_FLAG_POLE_BLUE_X]
        y = self.__settings[KEY_FLAG_POLE_BLUE_Y]
        z = self.__settings[KEY_FLAG_POLE_BLUE_Z]
        return Vector3(x, y, z)
    
    @flag_pole_pos_blue.setter
    def flag_pole_pos_blue(self, value):
        """Sets the position of the blue flag pole.
        
        Keyword arguments:
        value -- Value to set the position to
        
        """
        self.__settings[KEY_FLAG_POLE_BLUE_X] = value.x
        self.__settings[KEY_FLAG_POLE_BLUE_Y] = value.y
        self.__settings[KEY_FLAG_POLE_BLUE_Z] = value.z
        self.flag_pole_blue.pos = value
        self.__save_settings()
    
        
def get_class():
    """Returns the ServerScript class for use by cuwo."""
    return CaptureTheFlagScript

    
@command
@admin
def setflagpoler(script):
    """Command for setting the flag pole of the red team."""
    player = script.get_player(None)
    if player is not None:
        ctfscript = script.server.scripts.capture_the_flag
        if isinstance(ctfscript.game_state, PreGameState):
            p = player.position
            pos = Vector3(p.x, p.y, p.z - 50000)
            ctfscript.flag_pole_pos_red = pos
            ctfscript.flag_red.pos = pos
            return 'Successful set red flag pole position.'
        else:
            return ('Flag poles can only be set when no match is ' +
                'running.')
    else:
        return ("The command 'setflagpoler' has to be run by a "
            "player.")
            
            
@command
@admin
def setflagpoleb(script):
    """Command for setting the flag pole of the blue team."""
    player = script.get_player(None)
    if player is not None:
        ctfscript = script.server.scripts.capture_the_flag
        if isinstance(ctfscript.game_state, PreGameState):
            ctfscript = script.server.scripts.capture_the_flag
            p = player.position
            pos = Vector3(p.x, p.y, p.z - 50000)
            ctfscript.flag_pole_pos_blue = pos
            ctfscript.flag_blue.pos = pos
            return 'Successful set blue flag pole position.'
        else:
            return ('Flag poles can only be set when no match is ' +
                'running.')
    else:
        return ("The command 'setflagpoleb' has to be run by a "
            "player.")

@command
@admin
def reloadconfig(script):
    """Command for reloading the config file."""
    ctfscript = script.server.scripts.capture_the_flag
    if isinstance(ctfscript.game_state, PreGameState):
        script.server.config.reload()
        ctfscript.load_config()
        return 'Config reloaded successful.'
    else:
        return ("This command can only be executed when no" +
            " match is running")
        
@command
@admin
def abortgame(script):
    """Command for aborting a running game."""
    ctfscript = script.server.scripts.capture_the_flag
    ctfscript.game_state = PreGameState(script.server, ctfscript)
    script.server.send_chat('Game aborted by administrator.')
    return 'Game successfully aborted.'

    
@command            
def startgame(script, match_mode='autobalance', point_count='1'):
    """Command for starting a game."""
    ctfscript = script.server.scripts.capture_the_flag
    match_mode = match_mode.lower()
    if match_mode != 'autobalance' and match_mode != 'choose':
        return "There is no matchmaking mode named '%s'." % \
            match_mode
    else:
        p = None
        try:
            p = int(point_count)
        except ValueError:
            p = None
        if p is None:
            return 'Could not parse %s.' % point_count
        else:
            if p <= 0:
                return 'You need at least on point to win.'
            else:
                return ctfscript.game_state.startgame(match_mode, p)
                
@command
def join(script, team=None):
    """Command for joining a team."""
    player = script.get_player(None)
    if player is None:
        return ("This command can't be issued from " +
            "server command line.")
    else:
        if team is None:
            return 'Please choose a team: blue or red'
        else:
            ctfscript = script.server.scripts.capture_the_flag
            return ctfscript.game_state.join(player, team)


def tpTo(ctfscript, player, location):
    if not isinstance(ctfscript.game_state, GameRunningState):
        if player is None:
            return "This command can't be executed from console."
        else:
            player.entity.teleport(location)
    else:
        return 'You can only teleport if no game is currently running.'


@command
def tptoredflag(script):
    ctfscript = script.server.scripts.capture_the_flag
    player = script.get_player(None)
    return tpTo(ctfscript, player, ctfscript.flag_pole_pos_red)


@command
def tptoblueflag(script):
    ctfscript = script.server.scripts.capture_the_flag
    player = script.get_player(None)
    return tpTo(ctfscript, player, ctfscript.flag_pole_pos_blue)