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
from datetime import datetime


from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.constants import HOSTILE_TYPE
from cuwo.constants import FRIENDLY_TYPE
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


# Keys used in config dict
CKEY_LOOTING_ENABLED = 'looting_enabled'
CKEY_XP_ON_KILL = 'xp_on_kill'
CKEY_XP_ON_WIN = 'xp_on_win'
CKEY_SPEED_CAP = 'speed_cap'
CKEY_RELATION_BETWEEN_MATCHES = 'relation_between_matches'


# Amount of XP a player receives if he kills another player with the
# same level
XP_ON_SAME_LEVEL = 25.0


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
        self.loot_manager = LootManager()
        error = self.load_config()
        if error is not None:
            print(('[ERROR][capture_the_flag]: %s' % error))
            print('Disabled capture_the_flag.')
            self.server.unload_script('capture_the_flag')
        else:
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
        """Loads the config from disk and sets default values if
        not contained.
        
        """
        try:
            c = self.server.load_data(CONFIG_FILE, {})
            
            save = False
            if CKEY_LOOTING_ENABLED not in c:
                c[CKEY_LOOTING_ENABLED] = True
                save = True
            if CKEY_XP_ON_KILL not in c:
                c[CKEY_XP_ON_KILL] = True
                save = True
            if CKEY_XP_ON_WIN not in c:
                c[CKEY_XP_ON_WIN] = False
                save = True
            if CKEY_SPEED_CAP not in c:
                c[CKEY_SPEED_CAP] = True
                save = True
            if CKEY_RELATION_BETWEEN_MATCHES not in c:
                c[CKEY_RELATION_BETWEEN_MATCHES] = \
                    'friendly_player'
                save = True
            
            # Check types
            if not isinstance(c[CKEY_LOOTING_ENABLED], bool):
                return 'Invalid value for %s.' % CKEY_LOOTING_ENABLED
            if not isinstance(c[CKEY_XP_ON_KILL], bool):
                return 'Invalid value for %s.' % CKEY_XP_ON_KILL
            if not isinstance(c[CKEY_XP_ON_WIN], bool):
                return 'Invalid value for %s.' % CKEY_XP_ON_WIN
            if not isinstance(c[CKEY_SPEED_CAP], bool):
                return 'Invalid value for %s.' % CKEY_SPEED_CAP
            l = ['friendly_player', 'friendly', 'hostile_player', 'hostile', 'neutral']
            if c[CKEY_RELATION_BETWEEN_MATCHES] not in l:
                s = 'Invalid value for '
                s = '%s%s.' % (s, CKEY_RELATION_BETWEEN_MATCHES)
                return '%s Allowed values are %s.' % (s, str(l)[1:-1])
            
            # Load config
            self.__config = c
            self.loot_manager.loot_enabled = self.loot_enabled
            
            if save:
                self.server.save_data(CONFIG_FILE, self.__config)
            
        except NameError as e:
            return 'Error while parsing config file.'
           
    def apply_config(self):
        """Applies the current config. Called after reloading
        config.
        
        """
        relation = self.relation_between_matches
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
        
    @property
    def loot_enabled(self):
        """Returns whether looting is enabled.
        
        Return value:
        True, if looting is enabled, otherwise False
        
        """
        return self.__settings[CKEY_LOOTING_ENABLED]
        
    @property
    def xp_on_kill(self):
        """Gets whether XP gainin on kill is enabled.
        
        Return value:
        True, if XP gaining is enabled, otherwise False
        
        """
        return self.__settings[CKEY_XP_ON_KILL]
        
    @property
    def xp_on_win(self):
        """Gets whether XP gaining on win is enabled.
        
        Return value:
        True, if XP gaining is enabled, otherwise false
        
        """
        return self.__settings[CKEY_XP_ON_WIN]
        
    @property
    def speed_cap(self):
        """Gets whether the speed cap for flag carriers is active.
        
        Return value:
            True, if the speed cap is active, otherwise False.
        
        """
        return self.__settings[CKEY_SPEED_CAP]
        
    @property
    def relation_between_matches(self):
        """Gets the relation setting for players when no match
        is running.
        
        Return value:
            Relation constant (see cubolt.constants).
        
        """
        key = self.__config[CKEY_RELATION_BETWEEN_MATCHES]
        return STRING_RELATION_MAPPING[key]
    
        
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
        error = ctfscript.load_config()
        if error is None:
            ctfscript.apply_config()
            return 'Config reloaded successful.'
        else:
            return error
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
