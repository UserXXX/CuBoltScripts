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
Utility classes for the "Capture the flag" script.
"""


import math


from cuwo.vector import Vector3


PARTICLES_NO_ACCELLERATION = 3
PARTICLES_NO_GRAVITY = 4


RADIUS = 100000


class Flagpole(object):
    def __init__(self, server, pos, color):
        self.server = server
        self.__pos = pos
        self.__color = color
        
        self.__particles = []
        self.__create_particles()
        
    def __create_particles(self):
        for i in range(8):
            p = self.server.create_particle_effect()
            p.data.pos = self.__calc_pos(self.__pos, i)
            p.data.accel = Vector3(0.0, 0.0, 0.0)
            p.data.color_red = self.__color.red
            p.data.color_blue = self.__color.green
            p.data.color_green = self.__color.blue
            p.data.color_alpha = self.__color.alpha
            p.data.scale = 0.5
            p.data.count = 1
            p.data.particle_type = PARTICLES_NO_ACCELLERATION
            p.data.spreading = 0.0
            p.data.something18 = 0
            p.interval = 3.0
            self.__particles.append(p)
            self.server.particle_effects.append(p)
            p.fire()
    
    def __calc_pos(self, pos, index):
        rotation = float(index) / 8.0 * math.pi * 2
        x = math.sin(rotation) * RADIUS + pos.x
        y = math.cos(rotation) * RADIUS + pos.y
        return Vector3(x, y, pos.z)
        
    def dispose(self):
        for effect in self.__particles:
            self.server.particle_effects.remove(effect)
        #self.__particles = []
    
    def __update_pos(self):
        #self.dispose()
        #self.__create_particles()
        for i in range(8):
            p = self.__particles[i]
            p.data.pos = self.__calc_pos(self.__pos, i)
            p.fire()
    
    @property
    def pos(self):
        return self.__pos
        
    @pos.setter
    def pos(self, value):
        self.__pos = value
        self.__update_pos()

        
class Flag(object):
    def __init__(self, server, pos, color):
        self.server = server
        self.__particle = server.create_particle_effect()
        p = self.__particle
        p.data.pos = pos
        p.data.accel = Vector3(0.0, 0.0, 2.0)
        p.data.color_red = color.red
        p.data.color_blue = color.green
        p.data.color_green = color.blue
        p.data.color_alpha = color.alpha
        p.data.scale = 0.5
        p.data.count = 5
        p.data.particle_type = PARTICLES_NO_GRAVITY
        p.data.spreading = 0.25
        p.data.something18 = 0
        self.server.particle_effects.append(p)
        p.interval = 0.1
        p.fire()
        
    @property
    def pos(self):
        return self.__particle.data.pos
        
    @pos.setter
    def pos(self, value):
        self.__particle.data.pos = value