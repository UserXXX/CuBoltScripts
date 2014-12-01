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


"""Game states and main game logic.
"""


import math

from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.entity import ItemData
from cuwo.entity import ItemUpgrade
from cuwo.packet import KillAction
from cuwo.packet import SoundAction
from cuwo.vector import Vector3


# Sounds
SOUND_LEVEL_UP = 29
SOUND_MISSION_COMPLETE = 30
SOUND_LICH_SCREAM = 43
SOUND_GATE = 51
SOUND_EXPLOSION = 81


# Some other constants
DEFAULT_REPLY = ('This command cannot be issued in the current state ' +
    'of the game.')
FLAG_POLE_DISTANCE = 500000
FLAG_CAPTURE_DISTANCE = 150000
HEAL_AMOUNT = 50000


# EntityUpdatePacket mask for transfer of the position
MASK_POSITION = 0


class GameState:
    """Parent class of all GameStates."""
    def __init__(self, server, ctfscript):
        """Initializes the GameState.
        
        Keyword arguments:
        server -- Current server instance
        ctfscript -- CaptureTheFlagServerScript instance
        
        """
        self.server = server
        self.ctfscript = ctfscript
    
    def update(self):
        """Method for handling update logic."""
        pass
        
    def on_leave(self):
        """Mehtod for handling (any) players leave."""
        pass
        
    def on_hit(self, attacker, target_entity):
        """Method for handling an on_hit event.
        
        Keyword arguments:
        attacker -- Attacking entity
        target_entity -- Attacked entity
        
        """
        return True
        
    def startgame(self, param1=None, param2=None, param3=None):
        """Method for handling a /startgame command.
        
        Keyword arguments:
        param1 -- Parameter given by the user
        param2 -- Parameter given by the user
        param3 -- Parameter given by the user
        
        Return value:
        Message to send the command executor
        
        """
        return DEFAULT_REPLY
        
    def join(self, player, team):
        """Method for handling a /join command.
        
        Keyword arguments:
        player -- The player who executed the command
        team -- The team he wants to join
        
        Return value:
        Message to send the command executor
        
        """
        return DEFAULT_REPLY
        
    def player_leave(self, player):
        """Method for handling a player leave event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        pass
        
    def player_join(self, player):
        """Method for handling a player join event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        pass
        
    def too_fast(self, player):
        """Method for handling a player moving too fast.
        
        Keyword arguments:
        player -- The player who was too fast
        
        """
        pass
            
    def _distance(self, v1, v2):
        """Calculates the distance between two vectors.
        
        Keyword arguments:
        v1 -- The first vector
        v2 -- The second vector
        
        Return value:
        The distance as a float
        
        """
        x = v1.x - v2.x
        y = v1.y - v2.y
        z = v1.z - v2.z
        return math.sqrt(x*x + y*y + z*z)
                    
    def _send_chat(self, msg, players):
        """Send a chat message to the given players.
        
        Keyword arguments:
        msg -- The message to send
        players -- The players to send the message to
        
        """
        for p in players:
            p.send_chat(msg)

        
class PreGameState(GameState):
    """State before the game starts (lobby)."""
    def __init__(self, server, ctfscript):
        """Creates a new PreGameState.
        
        server -- Current server instance
        ctfscript -- CaptureTheFlagServerScript instance
        
        """
        GameState.__init__(self, server, ctfscript)
        self.__match_mode = 'autobalance'
        ctfscript.flag_red.pos = ctfscript.flag_pole_pos_red
        ctfscript.flag_red.carrier = None
        ctfscript.flag_blue.pos = ctfscript.flag_pole_pos_blue
        ctfscript.flag_blue.carrier = None
        
        hostile = ctfscript.hostile_between_matches
        hostility = FRIENDLY_PLAYER_TYPE
        if hostile:
            hostility = ctfscript.hostility_between_matches
        server.entity_manager.set_hostility_all(hostile, hostility)
        
    def startgame(self, match_mode='autobalance', point_count=1, use_last=False):
        """Method for handling a /startgame command.
        
        Keyword arguments:
        match_mode -- Chosen match mode
        point_count -- Number of flags needed to win
        use_last -- True, to use last games settings, otherwise False
        
        Return value:
        Message to send the command executor
        
        """
        if len(self.server.players) > 1:
            if not use_last:
                self.__match_mode = match_mode
            
            if self.__match_mode == 'choose':
                self.ctfscript.game_state = GameChooseState(
                    self.server, self.ctfscript, self,
                    point_count)
            else:
                self.ctfscript.game_state = GameAutobalancingState(
                    self.server, self.ctfscript, self, point_count)
                
            em = self.server.entity_manager
            em.set_hostility_all(False, FRIENDLY_PLAYER_TYPE)
            
            return 'Game starting...'
        else:
            return 'Not enough players to start a match!'
               
               
class GameAutobalancingState(GameState):
    """State for autobalancing the teams."""
    def __init__(self, server, ctfscript, pre_game_state, point_count):
        """Creates a new GameAutobalancingState
        
        Keyword arguments:
        server -- Current server instance
        ctfscript -- CaptureTheFlagServerScript instance
        pre_game_state -- Last active game state
        point_count -- Number of flags needed to win
        
        """
        GameState.__init__(self, server, ctfscript)
        self.__pre_game_state = pre_game_state
        self.__point_count = point_count
        
    def update(self):
        """Method for handling update logic."""
        red = []
        blue = []
        point_count = self.__point_count
        
        self.__autobalance(red, blue)

        server = self.server
        ctf = self.ctfscript
        ctf.game_state = GameInitialisingState(server,
            self.ctfscript, self.__pre_game_state, red, blue,
            [], point_count)
            
    def __autobalance(self, red, blue):
        """Autobalances the teams.
        
        Keyword arguments:
        red -- List for the red players
        blue -- List for the blue players
        
        """
        players = self.server.players.values()
        players = sorted(players, key=lambda player: \
            -1*player.entity.level)
        r = 0
        b = 0
        for i in range(len(players)):
            p = players[i]
            if b >= r:
                r += p.entity.level
                red.append(p)
            else:
                b += p.entity.level
                blue.append(p)
                
                
class GameChooseState(GameState):
    """State for choosing teams."""
    def __init__(self, server, ctfscript, pre_game_state, point_count):
        """Creates a new GameAutobalancingState
        
        Keyword arguments:
        server -- Current server instance
        ctfscript -- CaptureTheFlagServerScript instance
        pre_game_state -- Last active game state
        point_count -- Number of flags needed to win
        
        """
        GameState.__init__(self, server, ctfscript)
        self.__pre_game_state = pre_game_state
        self.__point_count = point_count
        self.__to_choose = []
        self.__red = []
        self.__blue = []
        self.__spectators = []
        for player in server.players.values():
            self.__to_choose.append(player)
        self.server.send_chat("Choose your team using '/join <team>'")
            
    def update(self):
        """Method for handling update logic."""
        if len(self.__to_choose) == 0:
            if self.__check_teams():
                server = self.server
                ctf = self.ctfscript
                ctf.game_state = GameInitialisingState(server,
                    self.ctfscript, self.__pre_game_state, self.__red,
                    self.__blue, self.__spectators,
                    self.__point_count)
                
    def join(self, player, team):
        """Method for handling a /join command.
        
        Keyword arguments:
        player -- The player who executed the command
        team -- The team he wants to join
        
        Return value:
        Message to send the command executor
        
        """
        if team != 'red' and team != 'blue' and team != 'spectators':
            return 'Please choose a valid team.'
        else:
            self.__remove_player(player)
            
            if team == 'red':
                self.__red.append(player)
                self.server.send_chat(('%s joined the red ' +
                    'team.') % player.name)
            elif team == 'blue':
                self.__blue.append(player)
                self.server.send_chat(('%s joined the blue ' +
                    'team.') % player.name)
            else:
                self.__spectators.append(player)
                self.server.send_chat('%s joined the spectators.' %
                    player.name)
                
    def player_join(self, player):
        """Method for handling a player join event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        self.__to_choose.append(player)
        
    def player_leave(self, player):
        """Method for handling a player leave event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        self.__remove_player(player)
            
    def __remove_player(self, player):
        """Removes player from the choosing players.
        
        Keyword arguments:
        player -- Player to remove
        
        """
        if player in self.__to_choose:
            self.__to_choose.remove(player)
        elif player in self.__red:
            self.__red.remove(player)
        elif player in self.__blue:
            self.__blue.remove(player)
        elif player in self.__spectators:
            self.__spectators.remove(player)
                
    def __check_teams(self):
        """Checks whether the teams are valid.
        
        Return value:
        True, if the teams are valid, otherwise False.
        
        """
        return len(self.__red) > 0 and len(self.__blue) > 0
        
               
class GameInitialisingState(GameState):
    """State just before the game starts, time to got to your flag!"""
    def __init__(self, server, ctfscript, pre_game_state, red, blue,
        spectators, points):
        GameState.__init__(self, server, ctfscript)
        self.__red = red
        self.__blue = blue
        self.__pre_game_state = pre_game_state
        self.__spectators = spectators;
        self.__points = points
        
        lm = self.ctfscript.loot_manager
        lm.new_match()
        if lm.loot_enabled:
            self.server.send_chat(lm.pre_game_message)
        if points > 1:
            server.send_chat(('You need %i points to win the' + 
                ' match!') % points)
        else:
            server.send_chat('First flag stolen wins!')
        self._send_chat('Please go to the red base.', red)
        self._send_chat('Please go to the blue base.', blue)
        server.send_chat('The game is about to begin!')
        
    def update(self):
        """Method for handling update logic."""
        rfpos = self.ctfscript.flag_pole_red.pos
        s = self.ctfscript
        for p in self.__spectators:
            p.entity.pos = Vector3(0, 0, 0)
            p.entity.mask |= MASK_POSITION
        for p in self.__red:
            pos = p.position
            if self._distance(pos, rfpos) > FLAG_POLE_DISTANCE:
                return None
        bfpos = self.ctfscript.flag_pole_blue.pos
        for p in self.__blue:
            pos = p.position
            if self._distance(pos, bfpos) > FLAG_POLE_DISTANCE:
                return None
        s.game_state = GameRunningState(self.server, s, self.__red,
            self.__blue, self.__spectators, self.__points)
    
    def player_join(self, player):
        """Method for handling a player join event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        self.__spectators.append(player)
            
    def on_leave(self):
        """Mehtod for handling (any) players leave."""
        s = self.server
        self.ctfscript.game_state = self.__pre_game_state
        s.send_chat(self.__pre_game_state.startgame(None,
            self.__points, True))
        s.send_chat(('The game was not started because a player left' +
            ' the game.'))
        
       
class GameRunningState(GameState):
    """State for the running game."""
    def __init__(self, server, ctfscript, red, blue, spectators,
        points):
        GameState.__init__(self, server, ctfscript)
        self.__red = red
        self.__blue = blue
        self.__spectators = spectators
        self.__points_needed = points
        self.__points_blue = 0
        self.__points_red = 0
        em = self.server.entity_manager
        em.set_hostility_all(False, ENTITY_HOSTILITY_FRIENDLY)
        self.__make_friendly(self.__red)
        self.__make_friendly(self.__blue)
        self.__make_hostile(self.__red, self.__blue)
        for p in self.server.players.values():
            p.entity.heal(HEAL_AMOUNT)
        for child in ctfscript.children:
            child.init_game()
        self.server.send_chat('Go!')
        self.__play_sound(SOUND_EXPLOSION)
        
    def __make_friendly(self, players):
        """Makes the given players friendly to each other.
        
        Keyword arguments:
        players -- Players to make friendly
        
        """
        em = self.server.entity_manager
        for p1 in players:
            for p2 in players:
                em.set_hostility_id(p1.entity_id, p2.entity_id,
                    False, ENTITY_HOSTILITY_FRIENDLY_PLAYER)
                    
    def __make_hostile(self, players1, players2):
        """Makes the given player groups hostile to each other.
        
        Keyword arguments:
        players1 -- First group of players
        players2 -- Second group of players
        
        """
        em = self.server.entity_manager
        for p1 in players1:
            for p2 in players2:
                em.set_hostility_id(p1.entity_id, p2.entity_id,
                    True, ENTITY_HOSTILITY_HOSTILE)
                    
    def __play_sound(self, index):
        """Plays a sound for all clients.
        
        Keyword arguments:
        index -- Index of the sound to play
        """
        for p in self.server.players.values():
            sound = SoundAction()
            sound.sound_index = index
            sound.pitch = 1.0
            sound.volume = 1.0
            sound.pos = p.position
            self.server.update_packet.sound_actions.append(sound)
        
    def player_join(self, player):
        """Method for handling a player join event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        self.__spectators.append(player)
        em = self.server.entity_manager
        for p in self.server.players:
            em.set_hostility_id(player.entity_id, p.entity_id,
                False, ENTITY_HOSTILITY_FRIENDLY)
        
    def player_leave(self, player):
        """Method for handling a player leave event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        if player in self.__red:
            self.__red.remove(player)
            fb = self.ctfscript.flag_blue
            if fb.carrier == player:
                fb.carrier = None
                self.server.send_chat('The blue flag got dropped!')
        elif player in self.__blue:
            self.__blue.remove(player)
            fr = self.ctfscript.flag_red
            if fr.carrier == player:
                fr.carrier = None
                self.server.send_chat('The red flag got dropped!')
        elif player in self.__spectators:
            self.__spectators.remove(player)
        
        if not self.__red and not self.__blue:
            ctfscript = self.ctfscript
            server = self.server
            ctfscript.game_state = PreGameState(server, ctfscript)
            server.send_chat('Game aborted because all players left.')
    
    def on_hit(self, attacker, target_entity):
        """Method for handling an on_hit event.
        
        Keyword arguments:
        attacker -- Attacking entity
        target_entity -- Attacked entity
        
        """
        return attacker not in self.__spectators
        
    def too_fast(self, player):
        """Method for handling a player moving too fast.
        
        Keyword arguments:
        player -- The player who was too fast
        
        """
        s = self.ctfscript
        if s.flag_red.carrier == player:
            s.flag_red.carrier = None
            self.server.send_chat('The red flag got dropped!')
        elif s.flag_blue.carrier == player:
            s.flag_blue.carrier = None
            self.server.send_chat('The blue flag got dropped!')
        
    def update(self):
        """Method for handling update logic."""
        s = self.ctfscript
        r = self.__red
        b = self.__blue
        fr = s.flag_red
        fb = s.flag_blue
        fpr = s.flag_pole_red
        fpb = s.flag_pole_blue
        
        se = self.server
        
        for p in self.__spectators:
            p.entity.pos = Vector3(0, 0, 0)
            p.entity.mask |= MASK_POSITION
        
        if self.__handle_team(r, b, fr, fpr, fpb):
            self.__points_blue = self.__points_blue + 1
            if self.__points_blue < self.__points_needed:
                se.send_chat('Red: %i' % self.__points_red)
                se.send_chat('Blue: %i' % self.__points_blue)
                se.send_chat('The current score is:')
                se.send_chat('The blue team got one point!')
                self.__play_sound(SOUND_LEVEL_UP)
                fr.carrier = None
                fr.pos = fpr.pos
        if self.__handle_team(b, r, fb, fpb, fpr):
            self.__points_red = self.__points_red + 1
            if self.__points_red < self.__points_needed:
                se.send_chat('Red: %i' % self.__points_red)
                se.send_chat('Blue: %i' % self.__points_blue)
                se.send_chat('The current score is:')
                se.send_chat('The red team got one point!')
                self.__play_sound(SOUND_LEVEL_UP)
                fb.carrier = None
                fb.pos = fpb.pos
        
        pb = self.__points_blue >= self.__points_needed
        pr = self.__points_red >= self.__points_needed
        if pb or pr:
            if pr: # Red wins
                se.send_chat('Red team wins!')
                self.ctfscript.loot_manager.give_loot(self.__red)
                self.__give_xp(self.__red)
            elif pb: # Blue wins
                se.send_chat('Blue team wins!')
                self.ctfscript.loot_manager.give_loot(self.__blue)
                self.__give_xp(self.__blue)
            else: # Draw
                se.send_chat('The game ended in a draw!')
            self.__play_sound(SOUND_MISSION_COMPLETE)
            s.game_state = PreGameState(se, s)
        
    def __handle_team(self, team, enemy_team, own_flag,
        own_pole, enemy_pole):
        """Handles the update logic for one team.
        
        Keyword arguments:
        team -- Team to handle
        enemy_team -- Other team
        own_flag -- Flag of the handled team
        own_pole -- Flag pole of the handled team
        enemy_pole -- Flag pole of the other team
        
        """
        if own_flag.carrier is None:
            ofp = own_flag.pos
            if not self._equals(ofp, own_pole.pos):
                for p in team:
                    if p.entity.hp > 0:
                        pos = p.position
                        if self._distance(pos, ofp) < \
                            FLAG_CAPTURE_DISTANCE:
                            own_flag.pos = own_pole.pos
                            fn = own_flag.name
                            s = self.server
                            s.send_chat(('The %s flag has been ' +
                                'resetted!') % fn)
                            self.__play_sound(SOUND_GATE)
                            break
            for p in enemy_team:
                if p.entity.hp > 0:
                    pos = p.position
                    if self._distance(pos, ofp) < FLAG_CAPTURE_DISTANCE:
                        own_flag.carrier = p
                        fn = own_flag.name
                        n = p.entity.name
                        s = self.server
                        s.send_chat('%s picked up the %s flag!' % (n, fn))
                        self.__play_sound(SOUND_LICH_SCREAM)
                        break
        if own_flag.carrier is not None:
            if own_flag.carrier.entity.hp <= 0:
                # Carrier was killed
                own_flag.carrier = None
                fn = own_flag.name
                self.server.send_chat('The %s flag got dropped!' % fn)
                return False
            else:
                p = own_flag.carrier.position  
                own_flag.pos = p
                ep = enemy_pole.pos
                if self._distance(p, ep) < FLAG_CAPTURE_DISTANCE:
                    # Carrier (enemy) carried flag to his pole
                    return True
                else:
                    return False
        else:
            return False
            
    def __give_xp(self, players):
        """Gives XP to the given players.
        
        Keyword arguments:
        players -- Players who will gain the XP
        
        """
        xp = (len(self.__red) + len(self.__blue)) * \
            self.__points_needed
        item = ItemData()
        item.minus_modifier = 0
        item.flags = 0
        item.items = []
        for _ in range(32):
            item.items.append(ItemUpgrade())
        item.type = 13
        item.sub_type = 0
        item.modifier = 1
        item.rarity = 2
        item.material = 3
        item.level = xp
        
        for p in players:
            p.give_item(item)
            
    def _equals(self, v1, v2):
        """Checks if two vectors are equal.
        
        Keyword argument:
        v1 -- First vector
        v2 -- Second vector
        
        """
        return v1.x == v2.x and v1.y == v2.y and v1.z == v2.z       
