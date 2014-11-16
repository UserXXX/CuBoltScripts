# The MIT License (MIT)
#
# Copyright (c) 2014 Bjoern Lange
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# This script is based on the pvp script delivered with cuwo.


"""
More advanced PVP script than the cuwo's default one.
"""

from cuwo.packet import EntityUpdate
from cuwo.packet import KillAction
from cuwo.packet import ServerUpdate


from cuwo.script import ConnectionScript
from cuwo.script import ServerScript
from cuwo.script import command
from cuwo.script import admin


ENTITY_HOSTILITY_FRIENDLY_PLAYER = 0
ENTITY_HOSTILITY_HOSTILE = 1
ENTITY_HOSTILITY_FRIENDLY = 2


SAVE_FILE = 'advanced_pvp'


KEY_PVP_ENABLED = 'pvp_enabled'
KEY_NOTIFY_ON_KILL = 'notify_on_kill'
KEY_GAIN_XP = 'gain_xp'
KEY_PVP_DISPLAY = 'pvp_display'


class PVPConnectionScript(ConnectionScript):
    def on_join(self, event):
        self.parent.update_hostilities()
            
    def on_kill(self, event):
        # event is not called if an entity with a friendly display is killed
        if self.parent.gain_xp:
            kill_action = KillAction()
            kill_action.entity_id = self.connectionplayer.entity.entity_id
            kill_action.target_id = event.target.entity_id
            kill_action.xp_gained = self.calculate_xp(self.connection.player.entity.level, event.target.level)
        
            self.server.update_packet.kill_actions.append(kill_action)
        
        if self.parent.notify_on_kill:
            self.server.send_chat('%s killed %s!' % (self.connection.name, event.target.name))
        
    # helper methods
    def calculate_xp(self, killer_level, killed_level):
        return max(1, int(10.0 * float(killed_level) / float(killer_level)))        

class PVPScript(ServerScript):
    connection_class = PVPConnectionScript
    
    # events
    def on_load(self):
        self.settings = self.server.load_data(SAVE_FILE, {})
        if KEY_PVP_ENABLED not in self.settings:
            self.settings[KEY_PVP_ENABLED] = True
        if KEY_NOTIFY_ON_KILL not in self.settings:
            self.settings[KEY_NOTIFY_ON_KILL] = False
        if KEY_GAIN_XP not in self.settings:
            self.settings[KEY_GAIN_XP] = True
        if KEY_PVP_DISPLAY not in self.settings:
            self.settings[KEY_PVP_DISPLAY] = ENTITY_HOSTILITY_HOSTILE
            
        em = self.server.entity_manager
        em.default_hostile = self.pvp_enabled
        em.default_hostility = self.pvp_display_mode
    
    def get_mode(self, event):
        if self.pvp_enabled:
            return 'pvp'
        else:
            return 'default'
            
    def update_hostilities(self):
        em = self.server.entity_manager
        pvp = self.pvp_enabled
        mode = self.pvp_display_mode
        em.set_hostility_all(pvp, mode)
        em.default_hostile = pvp
        em.default_hostility = mode
            
    # helper methods
    def save_settings(self):
        self.server.save_data(SAVE_FILE, self.settings)
    
    @property
    def pvp_enabled(self):
        return self.settings[KEY_PVP_ENABLED]
        
    @pvp_enabled.setter
    def pvp_enabled(self, enabled):
        self.settings[KEY_PVP_ENABLED] = enabled
        self.save_settings()
        self.update_hostilities()
    
    @pvp_enabled.deleter
    def pvp_enabled(self):
        del self.settings[KEY_PVP_ENABLED]
    
    @property
    def notify_on_kill(self):
        return self.settings[KEY_NOTIFY_ON_KILL]
    
    @notify_on_kill.setter
    def notify_on_kill(self, enabled):
        self.settings[KEY_NOTIFY_ON_KILL] = enabled
        self.save_settings()
        
    @notify_on_kill.deleter
    def notify_on_kill(self):
        del self.settings[KEY_NOTIFY_ON_KILL]
    
    @property
    def gain_xp(self):
        return self.settings[KEY_GAIN_XP]
    
    @gain_xp.setter
    def gain_xp(self, gain):
        self.settings[KEY_GAIN_XP] = gain
        self.save_settings()
    
    @gain_xp.deleter
    def gain_xp(self):
        del self.settings[KEY_GAIN_XP]
    
    @property
    def pvp_display_mode(self):
        return self.settings[KEY_PVP_DISPLAY]
        
    @pvp_display_mode.setter
    def pvp_display_mode(self, display):
        self.settings[KEY_PVP_DISPLAY] = display
        self.save_settings()
        self.update_hostilities()
    
    @pvp_display_mode.deleter
    def pvp_display_mode(self):
        del self.settings[KEY_PVP_DISPLAY]
    

def get_class():
    return PVPScript
 
# pvp commands
@command
def pvp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.pvp_enabled:
        return 'PVP mode is active.'
    else:
        return 'PVP mode is not active.'

@command
@admin
def enablepvp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.pvp_enabled:
        return 'PVP is already enabled.'
    else:
        pvp_script.pvp_enabled = True
        return 'PVP has been enabled.'

@command
@admin
def disablepvp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if not pvp_script.pvp_enabled:
        return 'PVP is already disabled.'
    else:
        pvp_script.pvp_enabled = False
        return 'PVP has been disabled.'

@command
@admin
def togglepvp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.pvp_enabled:
        return disablepvp(script)
    else:
        return enablepvp(script)
        
# notify on kill commands
@command
def notifyonkill(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.notify_on_kill:
        return 'Kills are notified.'
    else:
        return 'Kills are not notified.'
        
@command
@admin
def enablenotifyonkill(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.notify_on_kill:
        return 'Kills are already notified.'
    else:
        pvp_script.notify_on_kill = True
        return 'Kills are now notified.'
        
@command
@admin
def disablenotifyonkill(script):
    pvp_script = script.server.scripts.advanced_pvp
    if not pvp_script.notify_on_kill:
        return 'Kills are already not notified.'
    else:
        pvp_script.notify_on_kill = False
        return 'Kills are no longer notified.'
        
@command
@admin
def togglenotifyonkill(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.notify_on_kill:
        return disablenotifyonkill(script)
    else:
        return enablenotifyonkill(script)

# gain xp commands        
@command
def gainxp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.gain_xp:
        return 'Players gain xp on player kills.'
    else:
        return "Players don't gain xp on player kills."
        
@command
@admin
def enablegainxp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.gain_xp:
        return 'Players already gain xp on player kills.'
    else:
        pvp_script.gain_xp = True
        return 'Players will now gain xp on player kills.'
        
@command
@admin
def disablegainxp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if not pvp_script.gain_xp:
        return "Players already don't gain xp on player kills."
    else:
        pvp_script.gain_xp = False
        return 'Players will no longer gain xp on player kills.'
        
@command
@admin
def togglegainxp(script):
    pvp_script = script.server.scripts.advanced_pvp
    if pvp_script.gain_xp:
        return disablegainxp(script)
    else:
        return enablegainxp(script)

# pvp displaymode command        
@command
def pvpdisplaymode(script):
    pvp_script = script.server.scripts.advanced_pvp
    dm = pvp_script.pvp_display_mode
    if dm == ENTITY_HOSTILITY_FRIENDLY_PLAYER:
        return 'In pvp mode, players are displayed as friendly entities and are shown on the map (setting: friendlyplayer).'
    elif dm == ENTITY_HOSTILITY_FRIENDLY:
        return 'In pvp mode, players are displayed as friendly entities (setting: friendly).'
    elif dm == ENTITY_HOSTILITY_HOSTILE:
        return 'In pvp mode, players are displayed as hostile entities (setting: hostile).'
    else:
        return 'Unknown setting, value=%i' % dm

@command
@admin
def setpvpdisplaymode(script, display):
    pvp_script = script.server.scripts.advanced_pvp
    if display == 'friendlyplayer':
        pvp_script.pvp_display_mode = ENTITY_HOSTILITY_FRIENDLY_PLAYER
        return 'In pvp mode, players are now displayed as friendly entities and are shown on the map.'
    elif display == 'friendly':
        pvp_script.pvp_display_mode = ENTITY_HOSTILITY_FRIENDLY
        return 'In pvp mode, players are now displayed as friendly entities.'
    elif display == 'hostile':
        pvp_script.pvp_display_mode = ENTITY_HOSTILITY_HOSTILE
        return 'In pvp mode, players are now displayed as hostile entities.'
    else:
        return 'Unknown mode: %s' % display
