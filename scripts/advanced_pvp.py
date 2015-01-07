# The MIT License (MIT)
#
# Copyright (c) 2014-2015 Bjoern Lange
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


import os.path


from cuwo.packet import EntityUpdate
from cuwo.packet import KillAction
from cuwo.packet import ServerUpdate


from cuwo.script import ConnectionScript
from cuwo.script import ServerScript
from cuwo.script import command
from cuwo.script import admin


SAVE_FILE = 'advanced_pvp'


KEY_NOTIFY_ON_KILL = 'notify_on_kill'
KEY_GAIN_XP = 'gain_xp'
KEY_RELATION_MODE = 'relation_mode'


# Relation constants from cubolt.constants
RELATION_FRIENDLY_PLAYER = 10
RELATION_FRIENDLY = 11
RELATION_FRIENDLY_NAME = 12
RELATION_HOSTILE_PLAYER = 13
RELATION_HOSTILE = 14
RELATION_NEUTRAL = 15
RELATION_TARGET = 16


RELATION_STRING_MAPPING = {
    RELATION_FRIENDLY_PLAYER : 'friendly_player',
    RELATION_FRIENDLY : 'friendly',
    RELATION_HOSTILE_PLAYER : 'hostile_player',
    RELATION_HOSTILE : 'hostile',
    RELATION_NEUTRAL : 'neutral'
}


STRING_RELATION_MAPPING = {
    'friendly_player' : RELATION_FRIENDLY_PLAYER,
    'friendly' : RELATION_FRIENDLY,
    'hostile_player' : RELATION_HOSTILE_PLAYER,
    'hostile' : RELATION_HOSTILE,
    'neutral' : RELATION_NEUTRAL
}


class PVPConnectionScript(ConnectionScript):
    def __init__(self, parent, connection):
        ConnectionScript.__init__(self, parent, connection)
        self.__joined = False

    def on_entity_update(self, event):
        if not self.__joined:
            self.parent.update_hostilities()
            self.__joined = True

    def on_kill(self, event):
        # event is not called if an entity with a friendly display is killed
        ce = self.connection.entity
        te = event.target
        if te is not NULL:
            # self NPC check is not neccessary, but in view on entity AI
            # implementation done here
            if te.is_player() and ce.is_player():
                if self.parent.gain_xp:
                    kill_action = KillAction()
                    kill_action.entity_id = ce.entity_id
                    kill_action.target_id = te.entity_id
                    kill_action.xp_gained = self.calculate_xp(self.connection.entity.level, event.target.level)
        
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
        if KEY_NOTIFY_ON_KILL not in self.settings:
            self.settings[KEY_NOTIFY_ON_KILL] = False
        if KEY_GAIN_XP not in self.settings:
            self.settings[KEY_GAIN_XP] = True
        if KEY_RELATION_MODE not in self.settings:
            self.settings[KEY_RELATION_MODE] = 'hostile'
    
    # cubolt events
    def on_relation_changed(self, event):
        from_entity = self.server.world.entities[event.entity_from_id]
        to_entity = self.server.world.entities[event.entity_to_id]
        relation = STRING_RELATION_MAPPING[self.relation_mode]
        if from_entity.is_player() and to_entity.is_player() and \
            relation != event.relation:
            from_entity.set_relation_to(to_entity, relation)

    def get_mode(self, event):
        rm = self.relation_mode
        if rm != RELATION_FRIENDLY_PLAYER and rm != RELATION_FRIENDLY:
            return 'pvp'
        else:
            return 'default'
            
    def update_hostilities(self):
        relation = STRING_RELATION_MAPPING[self.relation_mode]
        for p1 in self.server.players.values():
            for p2 in self.server.players.values():
                p1.entity.set_relation_to(p2.entity, relation)
            
    # helper methods
    def save_settings(self):
        if not os.path.exists('./save'):
            os.makedirs('./save')
        self.server.save_data(SAVE_FILE, self.settings)
    
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
    def relation_mode(self):
        return self.settings[KEY_RELATION_MODE]
        
    @relation_mode.setter
    def relation_mode(self, relation):
        self.settings[KEY_RELATION_MODE] = relation
        self.save_settings()
        self.update_hostilities()
    
    @relation_mode.deleter
    def relation_mode(self):
        del self.settings[KEY_RELATION_MODE]
    

def get_class():
    return PVPScript
    
        
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


# relation mode commands        
@command
def relationmode(script):
    pvp_script = script.server.scripts.advanced_pvp
    rm = pvp_script.relation_mode
    return 'The current relation mode is: %s' % rm


@command
@admin
def setrelationmode(script, relation):
    pvp_script = script.server.scripts.advanced_pvp
    if relation in STRING_RELATION_MAPPING.keys():
        pvp_script.relation_mode = relation
        return 'Successful set relation mode to %s.' % relation
    else:
        return 'Unknown mode: %s' % relation