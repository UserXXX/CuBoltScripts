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


import random


import time


from cuwo.script import ServerScript


class RandomEventScript(ServerScript):
    def on_load(self):
        self.time = time.time()
    
    def update(self, event):
        t = time.time()
        diff = t - self.time
        if diff > 30:
            self.time = t
            self.do_something()
            
    def do_something(self):
        entity_count = len(self.server.entity_list)
        if entity_count > 0:
            index = random.randint(0, entity_count - 1)
        
            i = 0
            entity_id = -1
            for id, data in self.server.entities.iteritems():
                if i == index:
                    entity_id = id
                    break
                i = i + 1
        
            entity = self.server.entity_list[entity_id]
        
            action = random.randint(0, 3)
            if action == 0:
                entity.damage(random.randint(500, 1000), random.randint(0, 5000))
                self.server.send_chat('Damaged %s!' % entity.data.name)
                print('Damaged %s!' % entity.data.name)
            elif action == 1:
                entity.heal(random.randint(500, 1000))
                self.server.send_chat('Healed %s!' % entity.data.name)
                print('Healed %s!' % entity.data.name)
            elif action == 2:
                entity.kill()
                self.server.send_chat('Killed %s!' % entity.data.name)
                print('Killed %s!' % entity.data.name)
            elif action == 3:
                entity.stun(random.randint(1000, 10000))
                self.server.send_chat('Stunned %s!' % entity.data.name)
                print('Stunned %s!' % entity.data.name)
                
def get_class():
    return RandomEventScript