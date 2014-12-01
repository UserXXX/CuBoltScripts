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


"""Capture the flag script for cuwo."""


import math
import os.path
from datetime import datetime


from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.packet import KillAction
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
CONFIG_FILE = '../config/capture_the_flag'


# Keys used in settings dict
KEY_FLAG_POLE_BLUE_X = 'flag_pole_blue_x'
KEY_FLAG_POLE_RED_X = 'flag_pole_red_x'
KEY_FLAG_POLE_BLUE_Y = 'flag_pole_blue_y'
KEY_FLAG_POLE_RED_Y = 'flag_pole_red_y'
KEY_FLAG_POLE_BLUE_Z = 'flag_pole_blue_z'
KEY_FLAG_POLE_RED_Z = 'flag_pole_red_z'
KEY_LOOTING_ENABLED = 'looting_enabled'
KEY_XP_ON_KILL = 'xp_on_kill'
KEY_XP_ON_WIN = 'xp_on_win'
KEY_SPEED_CAP = 'speed_cap'

# Keys used in config dict
CKEY_HOSTILE_BETWEEN_MATCHES = 'hostile_between_matches'
CKEY_HOSTILITY_BETWEEN_MATCHES = 'hostility_between_matches'


# Amount of XP a player receives if he kills another player with the
# same level
XP_ON_SAME_LEVEL = 25.0


# Movement speed cap and min update time
MOVEMENT_SPEED_CAP = 7500000
MOVEMENT_SPEED_FPS = 1 / 60


class CaptureTheFlagConnectionScript(ConnectionScript):
    """ConnectionScript handling a single players connection."""
    def on_join(self, event):
        """Handles cuwo's on_join event.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        self.parent.game_state.player_join(self.connection)
    
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
        if self.parent.xp_on_kill and target_id in self.server.players:
            entity_id = self.connection.entity_id
            kill_action = KillAction()
            kill_action.entity_id = entity_id
            kill_action.target_id = target_id
            xp = self.__calculate_xp(self.entity.level, event.target.level)
            kill_action.xp_gained = xp
            self.server.update_packet.kill_actions.append(kill_action)
            
    def on_pos_update(self, event):
        """Handles a position update of this player.
        
        Keyword arguments:
        event -- Further information about what happened
        
        """
        if self.parent.speed_cap:
            if isinstance(self.parent.game_state, GameRunningState):
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
        
    def __calculate_xp(self, killer_level, killed_level):
        """Calculates the amount of XP a player gains for a kill.
        
        Keyword arguments:
        killer_level -- Level of the killing entity
        killed_level -- Level of the killed entity
        
        Return value:
        The amount of XP the killer gains
        
        """
        tmp = float(killed_level) / float(killer_level)
        return max(1, int(XP_ON_SAME_LEVEL * tmp))


class CaptureTheFlagScript(ServerScript):
    """ServerScript managing CTF."""
    connection_class = CaptureTheFlagConnectionScript

    def on_load(self):
        """Handles the loading of this script."""
        self.__load_settings()
        self.__load_config()
        self.__create_flag_poles()
        self.loot_manager = LootManager()
        self.loot_manager.loot_enabled = self.loot_enabled
        self.game_state = PreGameState(self.server, self)
        
    def on_unload(self):
        """Handles the unloading of this script."""
        self.flag_pole_red.dispose()
        self.flag_pole_blue.dispose()
        
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
        if KEY_LOOTING_ENABLED not in self.__settings:
            self.__settings[KEY_LOOTING_ENABLED] = True
        if KEY_XP_ON_KILL not in self.__settings:
            self.__settings[KEY_XP_ON_KILL] = True
        if KEY_XP_ON_WIN not in self.__settings:
            self.__settings[KEY_XP_ON_WIN] = False
        if KEY_SPEED_CAP not in self.__settings:
            self.__settings[KEY_SPEED_CAP] = True
                
    def __load_config(self):
        self.__config = self.server.load_data(CONFIG_FILE, {})
        if CKEY_HOSTILE_BETWEEN_MATCHES not in self.__config:
            self.__config[CKEY_HOSTILE_BETWEEN_MATCHES] = False
        if CKEY_HOSTILITY_BETWEEN_MATCHES not in self.__config:
            self.__config[CKEY_HOSTILITY_BETWEEN_MATCHES] = \
                FRIENDLY_PLAYER_TYPE
        self.server.save_data(CONFIG_FILE, self.__config)
            
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
        
    @property
    def loot_enabled(self):
        """Returns whether looting is enabled.
        
        Return value:
        True, if looting is enabled, otherwise False
        
        """
        return self.__settings[KEY_LOOTING_ENABLED]
        
    @loot_enabled.setter
    def loot_enabled(self, value):
        """Sets whether looting is enabled.
        
        Keyword arguments:
        value -- True to enable or False to disable looting
        """
        self.loot_manager.loot_enabled = value
        self.__settings[KEY_LOOTING_ENABLED] = value
        self.__save_settings()
        
    @property
    def xp_on_kill(self):
        """Gets whether XP gainin on kill is enabled.
        
        Return value:
        True, if XP gaining is enabled, otherwise False
        
        """
        return self.__settings[KEY_XP_ON_KILL]
        
    @xp_on_kill.setter
    def xp_on_kill(self, value):
        """Sets whether XP gaining on kill is enabled.
        
        Keyword arguments:
        value -- True to enable of False to disable XP gaining
        
        """
        self.__settings[KEY_XP_ON_KILL] = value
        self.__save_settings()
        
    @property
    def xp_on_win(self):
        """Gets whether XP gaining on win is enabled.
        
        Return value:
        True, if XP gaining is enabled, otherwise false
        
        """
        return self.__settings[KEY_XP_ON_WIN]
    
    @xp_on_win.setter
    def xp_on_win(self, value):
        """Sets whether XP gaining on win is enabled.
        
        Keyword arguments:
        value -- True to enable or False to disable XP gaining
        
        """
        self.__settings[KEY_XP_ON_WIN] = value
        self.__save_settings()
        
    @property
    def speed_cap(self):
        """Gets whether the speed cap for flag carriers is active.
        
        Return value:
            True, if the speed cap is active, otherwise False.
        
        """
        return self.__settings[KEY_SPEED_CAP]
        
    @speed_cap.setter
    def speed_cap(self, value):
        """Sets whether the speed cap for flag carriers is active.
        
        Keyword arguments:
        value -- True to enable or False to disable the speed cap
            
        """
        self.__settings[KEY_SPEED_CAP] = value
        self.__save_settings()
        
    @property
    def hostile_between_matches(self):
        return self.__config[CKEY_HOSTILE_BETWEEN_MATCHES]
        
    @property
    def hostility_between_matches(self):
        return self.__config[CKEY_HOSTILITY_BETWEEN_MATCHES]
    
        
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
def loot(script, state=None):
    """Command for enabling, disabling or displaying the state of
    looting.
    
    """
    ctfscript = script.server.scripts.capture_the_flag
    if state is None:
        if ctfscript.loot_enabled:
            return 'Loot is enabled.'
        else:
            return 'Loot is disabled.'
    else:
        if isinstance(ctfscript.game_state, PreGameState):
            if state == 'on':
                if ctfscript.loot_enabled:
                    return 'Looting is already enabled.'
                else:
                    ctfscript.loot_enabled = True
                    return 'Looting has been enabled.'
            elif state == 'off':
                if ctfscript.loot_enabled:
                    ctfscript.loot_enabled = False
                    return 'Looting has been disabled.'
                else:
                    return 'Looting is already disabled.'
            else:
                return 'Unknown prameter: %s' % state
        else:
            return 'Looting can only be changed if no game is running.'
            

@command
@admin
def xponkill(script, state=None):
    """Command for enabling, disabling or displaying the state of
    XP gaining on kill.
    
    """
    ctfscript = script.server.scripts.capture_the_flag
    if state is None:
        if ctfscript.xp_on_kill:
            return 'XP on kill is enabled.'
        else:
            return 'XP on kill is disabled.'
    else:
        if isinstance(ctfscript.game_state, PreGameState):
            if state == 'on':
                if ctfscript.xp_on_kill:
                    return 'XP on kill is already enabled.'
                else:
                    ctfscript.xp_on_kill = True
                    return 'XP on kill has been enabled.'
            elif state == 'off':
                if ctfscript.xp_on_kill:
                    ctfscript.xp_on_kill = False
                    return 'XP on kill has been disabled.'
                else:
                    return 'XP on kill is already disabled.'
            else:
                return 'Unknown prameter: %s' % state
        else:
            return ('XP on kill can only be changed if no' +
                ' game is running.')
            

@command
@admin
def xponwin(script, state=None):
    """Command for enabling, disabling or displaying the state of
    XP gaining on win.
    
    """
    ctfscript = script.server.scripts.capture_the_flag
    if state is None:
        if ctfscript.xp_on_win:
            return 'XP on win is enabled.'
        else:
            return 'XP on win is disabled.'
    else:
        if isinstance(ctfscript.game_state, PreGameState):
            if state == 'on':
                if ctfscript.xp_on_win:
                    return 'XP on win is already enabled.'
                else:
                    ctfscript.xp_on_win = True
                    return 'XP on win has been enabled.'
            elif state == 'off':
                if ctfscript.xp_on_win:
                    ctfscript.xp_on_win = False
                    return 'XP on win has been disabled.'
                else:
                    return 'XP on win is already disabled.'
            else:
                return 'Unknown prameter: %s' % state
        else:
            return ('XP on win can only be changed if no' +
                ' game is running.')
            

@command
@admin
def speedcap(script, state=None):
    """Command for enabling, disabling or displaying the speed cap
    for flag carriers.
    
    """
    ctfscript = script.server.scripts.capture_the_flag
    if state is None:
        if ctfscript.speed_cap:
            return 'Speed cap is enabled.'
        else:
            return 'Speed cap is disabled.'
    else:
        if isinstance(ctfscript.game_state, PreGameState):
            if state == 'on':
                if ctfscript.speed_cap:
                    return 'Speed cap is already enabled.'
                else:
                    ctfscript.speed_cap = True
                    return 'Speed cap has been enabled.'
            elif state == 'off':
                if ctfscript.speed_cap:
                    ctfscript.speed_cap = False
                    return 'Speed cap has been disabled.'
                else:
                    return 'Speed cap is already disabled.'
            else:
                return 'Unknown prameter: %s' % state
        else:
            return ('Speed cap can only be changed if no' +
                ' game is running.')
            
        
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
