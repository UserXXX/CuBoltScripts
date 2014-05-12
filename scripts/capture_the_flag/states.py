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
Game states.
"""


import math


ENTITY_HOSTILITY_FRIENDLY_PLAYER = 0
ENTITY_HOSTILITY_HOSTILE = 1


DEFAULT_REPLY = ('This command cannot be issued in the current state ' +
    'of the game.')
FLAG_POLE_DISTANCE = 500000
FLAG_CAPTURE_DISTANCE = 50000


class GameState(object):
    def __init__(self, server, ctfscript):
        self.server = server
        self.ctfscript = ctfscript
    
    def update(self):
        pass
        
    def startgame(self, param1):
        return DEFAULT_REPLY
            
    def _distance(self, v1, v2):
        x = v1.x - v2.x
        y = v1.y - v2.y
        z = v1.z - v2.z
        return math.sqrt(x*x + y*y + z*z)

        
class PreGameState(GameState):
    def __init__(self, server, ctfscript):
        GameState.__init__(self, server, ctfscript)
        self.__match_mode = 'autobalance'
        ctfscript.flag_red.pos = ctfscript.flag_pole_pos_red
        ctfscript.flag_blue.pos = ctfscript.flag_pole_pos_blue
        server.entity_manager.set_hostility_all(False,
            ENTITY_HOSTILITY_FRIENDLY_PLAYER)
        
    def startgame(self, match_mode):
        if len(self.server.entity_list) > 1:
            if match_mode is None or match_mode == '':
                match_mode = 'autobalance'
            
            self.__match_mode = match_mode
            
            red = []
            blue = []
            self.__autobalance(red, blue)

            self.__send_chat('Please go to the red base.', red)
            self.__send_chat('Please go to the blue base.', blue)
            ctf = self.ctfscript
            ctf.game_state = GameInitialisingState(self.server,
                self.ctfscript, red, blue)
            return 'Game starting...'
        else:
            return 'Not enough players to start a match!'
            
    def __autobalance(self, red, blue):
        players = self.server.players.values()
        players = sorted(players, cmp=self.player_compare)
        r = 0
        b = 0
        for i in range(len(players)):
            p = players[i]
            if b >= r:
                r += p.entity_data.level
                red.append(p)
            else:
                b += p.entity_data.level
                blue.append(p)
        
    def player_compare(self, p1, p2):
        return int(p1.entity_data.level - p2.entity_data.level)
                    
    def __send_chat(self, msg, players):
        for p in players:
            p.send_chat(msg)
               
               
class GameInitialisingState(GameState):
    def __init__(self, server, ctfscript, red, blue):
        GameState.__init__(self, server, ctfscript)
        self.__red = red
        self.__blue = blue
        
    def update(self):
        rfpos = self.ctfscript.flag_pole_red.pos
        s = self.ctfscript
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
            self.__blue)
       
       
class GameRunningState(GameState):
    def __init__(self, server, ctfscript, red, blue):
        GameState.__init__(self, server, ctfscript)
        self.__red = red
        self.__blue = blue
        em = self.server.entity_manager
        em.set_hostility_all(True, ENTITY_HOSTILITY_HOSTILE)
        self.__make_friendly(self.__red)
        self.__make_friendly(self.__blue)
        self.server.send_chat('Go!')
        
    def __make_friendly(self, players):
        em = self.server.entity_manager
        for p1 in players:
            for p2 in players:
                em.set_hostility_id(p1.entity_id, p2.entity_id,
                    False, ENTITY_HOSTILITY_FRIENDLY_PLAYER)
        
    def update(self):
        s = self.ctfscript
        r = self.__red
        b = self.__blue
        fr = s.flag_red
        fb = s.flag_blue
        fpr = s.flag_pole_red
        fpb = s.flag_pole_blue
        self.__handle_flag(fr, fpb, b, fpr, r, 'Blue team wins!')
        self.__handle_flag(fb, fpr, r, fpb, b, 'Red team wins!')
        
    def __handle_flag(self, flag, pole, team, enemy_pole, enemies,
        victory_msg):
        if flag.carrier is None:
            fp = flag.pos
            for p in team:
                pos = p.position
                if self._distance(pos, fp) < FLAG_CAPTURE_DISTANCE:
                    flag.pos = pole.pos
            for p in enemies:
                pos = p.position
                if self._distance(pos, fp) < FLAG_CAPTURE_DISTANCE:
                    flag.carrier = p
                    flag.pos = flag.carrier.position
        else:
            if flag.carrier.hp <= 0:
                flag.carrier = None
            else:
                p = flag.carrier.position
                flag.pos = p
                ep = enemy_pole.pos
                if self._distance(p, ep) < FLAG_CAPTURE_DISTANCE:
                    s = self.server
                    s.send_chat(victory_msg)
                    ctf = self.ctfscript
                    ctf.game_state = PreGameState(s, ctf)