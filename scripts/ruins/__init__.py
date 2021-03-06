# The MIT License (MIT)
#
# Copyright (c) 2015 Bjoern Lange
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


"""Ruins spawning script for CuBolt."""


import shutil

from os import listdir
from os.path import isfile
from os.path import join

from cuwo.script import ServerScript
from cuwo.tgen import EMPTY_TYPE
from cuwo.tgen import WATER_TYPE
from cuwo.tgen import FLATWATER_TYPE
from cuwo.tgen import WOOD_TYPE
from cuwo.tgen import LEAF_TYPE


MODEL_PATH = 'scripts/ruins/models/'
THRESHOLD = 0
IGNORED_TYPES = [EMPTY_TYPE, WATER_TYPE, FLATWATER_TYPE, WOOD_TYPE,
                 LEAF_TYPE]


DEFAULT_CONFIG_FILE = 'scripts/ruins/default_config.py'
CONFIG_FILE = 'config/ruins.py'


class DefaultModelLoader:
    """Default model loader, holding all necessary methods."""
    def __init__(self, server, path):
        """Creates a new DefaultModelLoader."""
        self.server = server
        self.path = path

    def load_model(self):
        """Loads the model described by the path given to __init__."""
        factory = self.server.cubolt_factory
        m = factory.load_model(self.path)
        self.post_process(m)
        return m

    def post_process(self, model):
        """Post processes the loaded model."""
        pass


class RotLeftModelLoader(DefaultModelLoader):
    """Model loader that rotates the model 90 degrees left after loading."""
    def __init__(self, server, path):
        DefaultModelLoader.__init__(self, server, path)

    def post_process(self, model):
        model.rotate_left_z()

        
class RotRightModelLoader(DefaultModelLoader):
    """Model loader that rotates the model 90 degrees right after loading."""
    def __init__(self, server, path):
        DefaultModelLoader.__init__(self, server, path)

    def post_process(self, model):
        model.rotate_right_z()


class Rot180ModelLoader(DefaultModelLoader):
    """Model loader that rotates the model for 180 degrees after loading."""
    def __init__(self, server, path):
        DefaultModelLoader.__init__(self, server, path)

    def post_process(self, model):
        model.rotate_180_z()


class MirrorXModelLoader(DefaultModelLoader):
    """Model loader that mirrors the model at the x plane after loading."""
    def __init__(self, server, path):
        DefaultModelLoader.__init__(self, server, path)

    def post_process(self, model):
        model.mirror_x()


class MirrorYModelLoader(DefaultModelLoader):
    """Model loader that mirrors the model at the y plane after loading."""
    def __init__(self, server, path):
        DefaultModelLoader.__init__(self, server, path)

    def post_process(self, model):
        model.mirror_y()


class RuinsScript(ServerScript):
    """Main script."""
    def on_load(self):
        """Initializes the script."""
        # Try to load the config and copy the default one if it fails
        try:
            self.server.config.ruins
        except (KeyError, FileNotFoundError):
            shutil.copyfile(DEFAULT_CONFIG_FILE, CONFIG_FILE)
            self.server.config.ruins

        # Get the seed and create the model loaders
        self.seed = int(self.server.config.base.seed)
        self.model_loaders = []
        files = [join(MODEL_PATH, f) for f in listdir(MODEL_PATH)
                 if isfile(join(MODEL_PATH, f)) and
                 f.endswith('.cub')]
        server = self.server
        for file in files:
            self.model_loaders.append(DefaultModelLoader(server, file))
            self.model_loaders.append(RotLeftModelLoader(server, file))
            self.model_loaders.append(RotRightModelLoader(server, file))
            self.model_loaders.append(Rot180ModelLoader(server, file))
            self.model_loaders.append(MirrorXModelLoader(server, file))
            self.model_loaders.append(MirrorYModelLoader(server, file))

    def on_chunk_load(self, event):
        """Called when a chunk has finished loading. This is a CuBolt event.
        
        Keyword arguments:
        event -- The event.

        """
        chunk = event.chunk
        # Get the grid noise value for this chunk
        n = self.noise(int(chunk.pos.x), int(chunk.pos.y))
        # Only if this value is over the threshold, try to spawn a ruin
        if n > self.server.config.ruins.threshold:
            index = n % len(self.model_loaders)

            # Load the chosen model via it's model loader instance
            model = self.model_loaders[index].load_model()

            # Calculate the models bounds within the chunk
            lower_x = self.noise(int(chunk.pos.x) + 21, int(chunk.pos.y) - 42)
            lower_y = self.noise(int(chunk.pos.x) - 42, int(chunk.pos.y) + 21)
            lower_x = min(lower_x, int(256 - model.size.x))
            lower_y = min(lower_y, int(256 - model.size.y))

            upper_x = lower_x + int(model.size.x)
            upper_y = lower_y + int(model.size.y)

            lower_z, upper_z = self.get_heights(chunk, lower_x, lower_y,
                                                upper_x, upper_y)

            # If the height difference is too large (e.g. the model
            # ranges over a cliff or hang) no ruin is generated 
            if (upper_z - lower_z) < 0.4 * model.size.z:
                # Calculate the absolute world position and place the model
                lx = lower_x + 256 * chunk.pos.x
                ly = lower_y + 256 * chunk.pos.y
                model.place_in_world(lx, ly, lower_z, 1)

    def get_heights(self, chunk, lx, ly, ux, uy):
        """Gets the minimum and maximum heights in an area of a chunk.
        
        Keyword arguments:
        chunk -- The chunk.
        lx -- Lower x coordinate.
        ly -- Lower y coordinate.
        ux -- Upper x coordinate.
        uy -- Upper y coordinate.

        """
        min = 100000
        max = 0
        cd = chunk.data
        for x in range(lx, ux + 1):
            for y in range(ly, uy + 1):
                h = cd.get_height(x, y)
                col = cd.get_column(x, y)
                type = col.get_block(h - 1).type
                while type in IGNORED_TYPES:
                    h = h - 1
                    type = col.get_block(h - 1).type
                if h < min:
                    min = h
                if h > max:
                    max = h
        return (min, max)

    def hash_32_shift(self, key):
        """Int hash function, range limited to 128.
        
        Keyword arguments:
        key -- Key to hash.

        """
        key = int(~key + int(key << 15))
        key = int(key ^ int(key >> 12))
        key = int(key + int(key << 2))
        key = int(key ^ int(key >> 4))
        key = int(key * 2057)
        key = int(key ^ int(key >> 16))
        return key % 128

    def noise(self, x, y):
        """Seeded grid noise function, based on an int hash.
        
        Keyword arguments:
        x -- X coordinate.
        y -- Y coordinate.

        """
        y_hash = self.hash_32_shift(y)
        x_hash = self.hash_32_shift(x + y_hash)
        return self.hash_32_shift(self.seed + x_hash)

def get_class():
    """Returns the ServerScript class for use by cuwo."""
    return RuinsScript