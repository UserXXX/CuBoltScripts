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


"""Game states and main game logic.
"""


from datetime import datetime
import math


from cuwo.constants import BLOCK_SCALE
from cuwo.constants import FRIENDLY_PLAYER_TYPE
from cuwo.entity import ItemData
from cuwo.entity import ItemUpgrade
from cuwo.packet import KillAction
from cuwo.packet import SoundAction
from cuwo.vector import Vector3


from .constants import RELATION_FRIENDLY_PLAYER
from .constants import RELATION_FRIENDLY
from .constants import RELATION_HOSTILE


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

    def on_kill(self, killer, killed):
        """Method for handling a kill event.

        Keyword arguments:
        killer -- Killing entity
        killed -- Killed entity

        """
        pass
        
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

    def on_respawn(self, entity):
        """Called when a player respawned.
        
        Keyword arguments:
        entity -- The respawned entity.
        
        """
            
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
            
    def _set_relation_all(self, relation):
        for p1 in self.server.players.values():
            for p2 in self.server.players.values():
                p1.entity.set_relation_to(p2.entity, relation)
        
    def _calculate_xp(self, killer_level, killed_level):
        """Calculates the amount of XP a player gains for a kill.
        
        Keyword arguments:
        killer_level -- Level of the killing entity
        killed_level -- Level of the killed entity
        
        Return value:
        The amount of XP the killer gains
        
        """
        tmp = float(killed_level) / float(killer_level)
        config = self.server.config
        return max(1, int(config.capture_the_flag.xp_on_same_level * tmp))

        
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
        
        relation = server.config.capture_the_flag.relation_between_matches
        self._set_relation_all(relation)

    def player_join(self, player):
        relation = self.server.config.capture_the_flag.relation_between_matches
        self._set_relation_all(relation)
        
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
                
            self._set_relation_all(RELATION_FRIENDLY_PLAYER)
            
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
        relation = self.server.config.capture_the_flag.relation_between_matches
        self._set_relation_all(relation)
        
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
        if server.config.capture_the_flag.loot:
            self.server.send_chat(lm.pre_game_message)
        if points > 1:
            server.send_chat(('You need %i points to win the' + 
                ' match!') % points)
        else:
            server.send_chat('First flag stolen wins!')
        self._send_chat('You are in the red team.', red)
        self._send_chat('You are in the blue team.', blue)
        server.send_chat('The game is about to begin!')
        self.__counter = 11.0
        self.__last_time = datetime.now()
        
    def update(self):
        """Method for handling update logic."""
        s = self.ctfscript
        for p in self.__spectators:
            p.entity.pos = Vector3(0, 0, 0)
            p.entity.mask |= MASK_POSITION

        now = datetime.now()
        dif = (now - self.__last_time).total_seconds()
        self.__last_time = now
        last_counter = self.__counter
        self.__counter = last_counter - dif
        new_ceil = math.ceil(self.__counter)
        old_floor = math.floor(last_counter)
        if new_ceil == old_floor and new_ceil > 0 and new_ceil < 11:
            self.server.send_chat('%i' % new_ceil)
        if self.__counter < 0:
            s.game_state = GameRunningState(self.server, s, self.__red,
                self.__blue, self.__spectators, self.__points)
    
    def player_join(self, player):
        """Method for handling a player join event.
        
        Keyword arguments:
        player -- The player who left
        
        """
        self.__spectators.append(player)
        relation = self.server.config.capture_the_flag.relation_between_matches
        self._set_relation_all(relation)
            
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
        self._set_relation_all(RELATION_FRIENDLY_PLAYER)
        self.__make_friendly(self.__red)
        self.__make_friendly(self.__blue)
        self.__make_hostile(self.__red, self.__blue)
        
        fpb = ctfscript.flag_pole_pos_blue
        fpr = ctfscript.flag_pole_pos_red
        self.__arena_center = fpr.xy + 0.5 * (fpb.xy - fpr.xy)
        self.__arena_size = 2 * abs(fpr.xy - fpb.xy)
        
        for p in blue:
            p.entity.teleport(fpb)
            p.entity.heal(p.entity.get_max_hp())
            p.port_immune_time = 0
        for p in red:
            p.entity.teleport(fpr)
            p.entity.heal(p.entity.get_max_hp())
            p.port_immune_time = 0
        for c in ctfscript.children:
            c.init_game()

        self.server.send_chat('Go!')
        self.__play_sound(SOUND_EXPLOSION)

        self.__last_time = datetime.now()
        
    def __make_friendly(self, players):
        """Makes the given players friendly to each other.
        
        Keyword arguments:
        players -- Players to make friendly
        
        """
        for p1 in players:
            for p2 in players:
                p1.entity.set_relation_to(p2.entity, RELATION_FRIENDLY_PLAYER)
                    
    def __make_hostile(self, players1, players2):
        """Makes the given player groups hostile to each other.
        
        Keyword arguments:
        players1 -- First group of players
        players2 -- Second group of players
        
        """
        for p1 in players1:
            for p2 in players2:
                p1.entity.set_relation_both(p2.entity, RELATION_HOSTILE)
                    
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
        for p in self.server.players:
            p.entity.set_relation_to(player, RELATION_FRIENDLY)
        
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

    def on_kill(self, killer, killed):
        """Method for handling a kill event.

        Keyword arguments:
        killer -- Killing entity
        killed -- Killed entity

        """
        if self.server.config.capture_the_flag.xp_on_kill:
            kill_action = KillAction()
            kill_action.entity_id = killer.entity_id
            kill_action.target_id = killed.entity_id
            xp = self._calculate_xp(killer.level, killed.level)
            kill_action.xp_gained = xp
            self.server.update_packet.kill_actions.append(kill_action)
        
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
        
    def on_respawn(self, entity):
        """Called when a player respawned.
        
        Keyword arguments:
        entity -- The respawned entity.
        
        """
        s = self.ctfscript
        player = self.server.players[entity.entity_id]
        player.port_immune_time = 3.0
        if player in self.__blue:
            entity.teleport(s.flag_pole_pos_blue)
        elif player in self.__red:
            entity.teleport(s.flag_pole_pos_red)

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

        now = datetime.now()
        dif = (now - self.__last_time).total_seconds()
        self.__last_time = now

        for p in (self.__red + self.__blue):
            if p.port_immune_time > 0:
                p.port_immune_time = p.port_immune_time - dif
                continue

            if abs(p.entity.pos.xy - self.__arena_center) > self.__arena_size:
                # Out of arena
                to_center = self.__arena_center - p.entity.pos.xy
                to_center.normalize()
                to_center = to_center * 20 * BLOCK_SCALE
                pos = p.entity.pos
                new_pos = Vector3(pos.x + to_center.x, pos.y + to_center.y, 0)
                world = self.ctfscript.world
                new_pos.z = world.get_height(new_pos.xy) or pos.z
                p.entity.teleport(new_pos)
        
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
        if self.server.config.capture_the_flag.xp_on_win:
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
