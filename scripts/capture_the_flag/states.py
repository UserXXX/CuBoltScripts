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


ENTITY_HOSTILITY_FRIENDLY_PLAYER = 0
ENTITY_HOSTILITY_HOSTILE = 1


DEFAULT_REPLY = ('This command cannot be issued in the current state ' +
    'of the game.')

    
class GameState(object):
    def __init__(self, server, ctfscript):
        self.server = server
        self.ctfscript = ctfscript
    
    def update(self):
        pass
        
    def startgame(self, param1):
        return DEFAULT_REPLY

        
class PreGameState(GameState):
    def __init__(self, server, ctfscript):
        GameState.__init__(self, server, ctfscript)
        self.__match_mode = 'autobalance'
        self.__red = []
        self.__blue = []
        
    def startgame(self, match_mode):
        if len(self.server.entity_list) > 1:
            if match_mode is None or match_mode == '':
                match_mode = 'autobalance'
            
            self.__match_mode = match_mode
            
            self.__red = []
            self.__blue = []
            self.__autobalance()

            em = self.server.entity_manager
            em.set_hostility_all(True, ENTITY_HOSTILITY_HOSTILE)
            self.__make_friendly(self.__red)
            self.__make_friendly(self.__blue)
            self.__send_chat('Please go to the red base.',
                self.__red)
            self.__send_chat('Please go to the blue base.',
                self.__blue)
            ctf = self.ctfscript
            ctf.game_state = GameInitialisingState(self.server,
                self.ctfscript, self.__red, self.__blue)
            return 'Game starting...'
        else:
            return 'Not enough players to start a match!'
            
    def __autobalance(self):
        pass #greedy autobalance algorithm
        
    def __make_friendly(self, players):
        em = self.server.entity_manager
        for p1 in players:
            for p2 in players:
                em.set_hostility_id(p1.entity_id, p2.entity_id,
                    False, ENTITY_HOSTILITY_FRIENDLY_PLAYER)
                    
    def __send_chat(self, msg, players):
        for p in players:
            p.send_chat(msg)
                    
class GameInitialisingState(GameState):
    def __init__(self, server, ctfscript, red, blue):
        GameState.__init__(self, server, ctfscript)
        
    