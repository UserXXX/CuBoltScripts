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


"""Utility classes for the "Capture the flag" script."""


import math


from cuwo.vector import Vector3


# Particle types
PARTICLES_NO_ACCELLERATION = 3
PARTICLES_NO_GRAVITY = 4


# Radius of flag poles
RADIUS = 100000


class Flagpole:
    """Flagpole."""
    def __init__(self, server, pos, color):
        """Creates a new Flagpole.
        
        Keyword arguments:
        server -- Server instance
        pos -- Position of this flag pole
        color -- Color of the flag pole
        
        """
        self.server = server
        self.__pos = pos
        self.__color = color
        
        self.__particles = []
        self.__create_particles()
        
    def __create_particles(self):
        """Creates a particle effect."""
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
        """Calculates the position of a flag pole part.
        
        Keyword arguments:
        pos -- Position of the flag pole
        index -- Index of the position to calculate
        """
        rotation = float(index) / 8.0 * math.pi * 2
        x = math.sin(rotation) * RADIUS + pos.x
        y = math.cos(rotation) * RADIUS + pos.y
        return Vector3(x, y, pos.z)
        
    def dispose(self):
        """Disposes the flag pole."""
        for effect in self.__particles:
            self.server.particle_effects.remove(effect)
        self.__particles = []
    
    def __update_pos(self):
        """Updates the position of the flagpole."""
        for i in range(8):
            p = self.__particles[i]
            p.data.pos = self.__calc_pos(self.__pos, i)
            p.fire()
    
    @property
    def pos(self):
        """Gets the position of the flagpole.
        
        Return value:
        The position of the flagpole
        """
        return self.__pos
        
    @pos.setter
    def pos(self, value):
        """Sets the position of the flagpole.
        
        Keyword arguments:
        value -- Value to set the position to
        """
        self.__pos = value
        self.__update_pos()

        
class Flag:
    """Flag."""
    def __init__(self, server, pos, color, name):
        """Creates a new flag.
        
        Keyword arguments:
        server -- Server instance
        pos -- Position of the flag
        color -- Color of the flag
        name -- Name of the flag
        
        """
        self.server = server
        self.__particle = server.create_particle_effect()
        self.carrier = None
        self.name = name
        p = self.__particle
        p.data.pos = pos
        p.data.accel = Vector3(0.0, 0.0, 2.0)
        p.data.color_red = color.red
        p.data.color_blue = color.green
        p.data.color_green = color.blue
        p.data.color_alpha = color.alpha
        p.data.scale = 0.5
        p.data.count = 1
        p.data.particle_type = PARTICLES_NO_GRAVITY
        p.data.spreading = 0.25
        p.data.something18 = 0
        self.server.particle_effects.append(p)
        p.interval = 0.05
        p.fire()
        
    @property
    def pos(self):
        """Gets the position of the flag.
        
        Return value:
        The position of the flag
        """
        return self.__particle.data.pos
        
    @pos.setter
    def pos(self, value):
        """Sets the position of the flag.
        
        Keyword arguments:
        value -- Value to set the position to
        """
        self.__particle.data.pos = value