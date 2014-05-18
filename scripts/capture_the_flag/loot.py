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
Loot management.
"""


import random


from cuwo.entity import ItemData
from cuwo.entity import ItemUpgrade


LOOT_COMMON = 0
LOOT_UNCOMMON = 1
LOOT_RARE = 2
LOOT_EPIC = 3
LOOT_LEGENDARY = 4
LOOT_SPIRIT_FIRE = 5
LOOT_SPIRIT_UNHOLY = 6
LOOT_SPIRIT_ICE = 7
LOOT_SPIRIT_WIND = 8
LOOT_MANA_CUBE = 9


CLASS_WARRIOR = 1
CLASS_RANGER = 2
CLASS_MAGE = 3
CLASS_ROGUE = 4


ITEM_TYPE_WEAPON = 3
ITEM_TYPE_ARMOR = 4
ITEM_TYPE_GLOVES = 5
ITEM_TYPE_BOOTS = 6
ITEM_TYPE_SHOULDER_ARMOR = 7
ITEM_TYPE_AMULET = 8
ITEM_TYPE_RING = 9
ITEM_TYPE_SPIRIT = 11


ITEM_SUB_TYPE_WEAPON_SWORD = 0
ITEM_SUB_TYPE_WEAPON_AXE = 1
ITEM_SUB_TYPE_WEAPON_MACE = 2
ITEM_SUB_TYPE_WEAPON_DAGGER = 3
ITEM_SUB_TYPE_WEAPON_FIST = 4
ITEM_SUB_TYPE_WEAPON_LONGSWORD = 5
ITEM_SUB_TYPE_WEAPON_BOW = 6
ITEM_SUB_TYPE_WEAPON_CROSSBOW = 7
ITEM_SUB_TYPE_WEAPON_BOOMERANG = 8
ITEM_SUB_TYPE_WEAPON_STAFF = 10
ITEM_SUB_TYPE_WEAPON_WAND = 11
ITEM_SUB_TYPE_WEAPON_BRACELET = 12
ITEM_SUB_TYPE_WEAPON_SHIELD = 13
ITEM_SUB_TYPE_WEAPON_GREATSWORD = 15
ITEM_SUB_TYPE_WEAPON_GREATAXE = 16
ITEM_SUB_TYPE_WEAPON_GREATMACE = 17


ITEM_SUB_TYPE_ARMOR = 0


ITEM_SUB_TYPE_GLOVES = 0


ITEM_SUB_TYPE_BOOTS = 0


ITEM_SUB_TYPE_SHOULDER_ARMOR = 0


ITEM_SUB_TYPE_AMULET = 0


ITEM_SUB_TYPE_RING = 0


ITEM_SUB_TYPE_SPIRIT = 14


MATERIAL_NONE = 0
MATERIAL_IRON = 1
MATERIAL_WOOD = 2
MATERIAL_GOLD = 11
MATERIAL_SILVER = 12
MATERIAL_SILK = 25
MATERIAL_LINEN = 26
MATERIAL_COTTON = 27


ITEM_RARITY_RARE = 2


class LootManager(object):
    def __init__(self):
        self.__loot = None
        self.loot_enabled = True
        self.__create_item_types()
        self.__create_material_data()
        self.__loots = {
            LOOT_COMMON : 'an common item', 
            LOOT_UNCOMMON : 'an uncommon item', 
            LOOT_RARE : 'an rare item', 
            LOOT_SPIRIT_FIRE : 'a fire spirit',
            LOOT_SPIRIT_WIND : 'a wind spirit',
            LOOT_SPIRIT_ICE : 'a ice spirit',
            LOOT_SPIRIT_UNHOLY : 'a unholy spirit',
            LOOT_EPIC : 'an epic item',
            LOOT_LEGENDARY : 'an legendary item',
            LOOT_MANA_CUBE : 'a mana cube'
        }
    
    def new_match(self):
        if self.__loot is None:
            self.__loot = self.__calc_loot()
            
    @property
    def pre_game_message(self):
        l = self.__loots[self.__loot]
        return ('The winners will receive %s each!') % l
        
    def give_loot(self, team):
        if self.loot_enabled:
            for player in team:
                player.give_item(self.__get_loot_item(player))
        self.__loot = None
    
    def __get_loot_item(self, player):
        l = self.__loot
        item = ItemData()
        item.minus_modifier = 0
        item.flags = 0
        item.items = []
        for _ in range(32):
            item.items.append(ItemUpgrade())
        item.upgrade_count = 0
        if l >= LOOT_COMMON and l <= LOOT_LEGENDARY:
            item.type = random.randint(ITEM_TYPE_WEAPON,
                ITEM_TYPE_RING)
            item.sub_type = self.__get_sub_type(item.type, player)
            item.modifier = random.randint(1, 10)
            item.rarity = l
            item.material = self.__get_material(item.type,
                item.sub_type, player)
            item.level = player.entity_data.level
        elif l >= LOOT_SPIRIT_FIRE and l <= LOOT_SPIRIT_WIND:
            item.type = ITEM_TYPE_SPIRIT
            item.sub_type = ITEM_SUB_TYPE_SPIRIT
            item.modifier = 0
            item.rarity = ITEM_RARITY_RARE
            # 128: Fire, 129: Unholy, 130: Ice, 131: Wind
            item.material = 123 + l
            item.level = player.entity_data.level
        else: # Mana Cube
            item.type = 25
            item.sub_type = 0
            item.modifier = 0
            item.rarity = 0
            item.material = 0
            item.level = 0
        return item
            
    def __get_sub_type(self, type, player):
        item_type = self.__item_types[type]
        item_player = item_type[player.entity_data.class_type]
        return item_player[random.randint(0, len(item_player) - 1)]
    
    def __get_material(self, type, sub_type, player):
        item_type = self.__item_materials[type]
        class_type = item_type[player.entity_data.class_type]
        sub_type = class_type[sub_type]
        return sub_type[random.randint(0, len(sub_type) - 1)]
    
    def __calc_loot(self):
        l = random.randint(0, 200)
        if l < 100:
            return LOOT_COMMON
        elif l < 150:
            return LOOT_UNCOMMON
        elif l < 165:
            return LOOT_RARE
        elif l < 170:
            return LOOT_EPIC
        elif l < 176:
            return LOOT_LEGENDARY
        elif l < 180:
            return LOOT_MANA_CUBE
        else:
            l = random.randint(0, 3)
            if l == 0:
                return LOOT_SPIRIT_FIRE
            elif l == 0:
                return LOOT_SPIRIT_WIND
            elif l == 0:
                return LOOT_SPIRIT_ICE
            else:
                return LOOT_SPIRIT_UNHOLY
                
    def __create_item_types(self):
        warrior_weapons = [
            ITEM_SUB_TYPE_WEAPON_SWORD,
            ITEM_SUB_TYPE_WEAPON_AXE,
            ITEM_SUB_TYPE_WEAPON_MACE,
            ITEM_SUB_TYPE_WEAPON_SHIELD,
            ITEM_SUB_TYPE_WEAPON_GREATSWORD,
            ITEM_SUB_TYPE_WEAPON_GREATAXE,
            ITEM_SUB_TYPE_WEAPON_GREATMACE
        ]
        
        ranger_weapons = [
            ITEM_SUB_TYPE_WEAPON_BOW,
            ITEM_SUB_TYPE_WEAPON_CROSSBOW,
            ITEM_SUB_TYPE_WEAPON_BOOMERANG
        ]
        
        mage_weapons = [
            ITEM_SUB_TYPE_WEAPON_STAFF,
            ITEM_SUB_TYPE_WEAPON_WAND,
            ITEM_SUB_TYPE_WEAPON_BRACELET
        ]
        
        rogue_weapons = [
            ITEM_SUB_TYPE_WEAPON_DAGGER,
            ITEM_SUB_TYPE_WEAPON_FIST,
            ITEM_SUB_TYPE_WEAPON_LONGSWORD
        ]
        
        weapons = {
            CLASS_WARRIOR : warrior_weapons,
            CLASS_RANGER : ranger_weapons,
            CLASS_MAGE : mage_weapons,
            CLASS_ROGUE : rogue_weapons
        }
        
        warrior_armors = [
            ITEM_SUB_TYPE_ARMOR
        ]
        
        ranger_armors = [
            ITEM_SUB_TYPE_ARMOR
        ]
        
        mage_armors = [
            ITEM_SUB_TYPE_ARMOR
        ]
        
        rogue_armors = [
            ITEM_SUB_TYPE_ARMOR
        ]
        
        armors = {
            CLASS_WARRIOR : warrior_armors,
            CLASS_RANGER : ranger_armors,
            CLASS_MAGE : mage_armors,
            CLASS_ROGUE : rogue_armors
        }
        
        warrior_gloves = [
            ITEM_SUB_TYPE_GLOVES
        ]
        
        ranger_gloves = [
            ITEM_SUB_TYPE_GLOVES
        ]
        
        mage_gloves = [
            ITEM_SUB_TYPE_GLOVES
        ]
        
        rogue_gloves = [
            ITEM_SUB_TYPE_GLOVES
        ]
        
        gloves = {
            CLASS_WARRIOR : warrior_gloves,
            CLASS_RANGER : ranger_gloves,
            CLASS_MAGE : mage_gloves,
            CLASS_ROGUE : rogue_gloves
        }
        
        warrior_boots = [
            ITEM_SUB_TYPE_BOOTS
        ]
        
        ranger_boots = [
            ITEM_SUB_TYPE_BOOTS
        ]
        
        mage_boots = [
            ITEM_SUB_TYPE_BOOTS
        ]
        
        rogue_boots = [
            ITEM_SUB_TYPE_BOOTS
        ]
        
        boots = {
            CLASS_WARRIOR : warrior_boots,
            CLASS_RANGER : ranger_boots,
            CLASS_MAGE : mage_boots,
            CLASS_ROGUE : rogue_boots
        }
        
        warrior_shoulder_armors = [
            ITEM_SUB_TYPE_SHOULDER_ARMOR
        ]
        
        ranger_shoulder_armors = [
            ITEM_SUB_TYPE_SHOULDER_ARMOR
        ]
        
        mage_shoulder_armors = [
            ITEM_SUB_TYPE_SHOULDER_ARMOR
        ]
        
        rogue_shoulder_armors = [
            ITEM_SUB_TYPE_SHOULDER_ARMOR
        ]
        
        shoulder_armors = {
            CLASS_WARRIOR : warrior_shoulder_armors,
            CLASS_RANGER : ranger_shoulder_armors,
            CLASS_MAGE : mage_shoulder_armors,
            CLASS_ROGUE : rogue_shoulder_armors
        }
        
        warrior_amulets = [
            ITEM_SUB_TYPE_AMULET
        ]
        
        ranger_amulets = [
            ITEM_SUB_TYPE_AMULET
        ]
        
        mage_amulets = [
            ITEM_SUB_TYPE_AMULET
        ]
        
        rogue_amulets = [
            ITEM_SUB_TYPE_AMULET
        ]
        
        amulets = {
            CLASS_WARRIOR : warrior_amulets,
            CLASS_RANGER : ranger_amulets,
            CLASS_MAGE : mage_amulets,
            CLASS_ROGUE : rogue_amulets
        }
        
        warrior_rings = [
            ITEM_SUB_TYPE_RING
        ]
        
        ranger_rings = [
            ITEM_SUB_TYPE_RING
        ]
        
        mage_rings = [
            ITEM_SUB_TYPE_RING
        ]
        
        rogue_rings = [
            ITEM_SUB_TYPE_RING
        ]
        
        rings = {
            CLASS_WARRIOR : warrior_rings,
            CLASS_RANGER : ranger_rings,
            CLASS_MAGE : mage_rings,
            CLASS_ROGUE : rogue_rings,
        }
        
        self.__item_types = {
            ITEM_TYPE_WEAPON : weapons,
            ITEM_TYPE_ARMOR : armors,
            ITEM_TYPE_GLOVES : gloves,
            ITEM_TYPE_BOOTS : boots,
            ITEM_TYPE_SHOULDER_ARMOR : shoulder_armors,
            ITEM_TYPE_AMULET : amulets,
            ITEM_TYPE_RING : rings
        }
        
    def __create_material_data(self):
        materials_sword = [
            MATERIAL_IRON
        ]
        
        materials_axe = [
            MATERIAL_IRON
        ]
        
        materials_mace = [
            MATERIAL_IRON
        ]
        
        materials_shield = [
            MATERIAL_IRON
        ]
        
        materials_greatsword = [
            MATERIAL_IRON
        ]
        
        materials_greataxe = [
            MATERIAL_IRON
        ]
        
        materials_greatmace = [
            MATERIAL_IRON
        ]
        
        warrior_weapons = {
            ITEM_SUB_TYPE_WEAPON_SWORD : materials_sword,
            ITEM_SUB_TYPE_WEAPON_AXE : materials_axe,
            ITEM_SUB_TYPE_WEAPON_MACE : materials_mace,
            ITEM_SUB_TYPE_WEAPON_SHIELD : materials_shield,
            ITEM_SUB_TYPE_WEAPON_GREATSWORD : materials_greatsword,
            ITEM_SUB_TYPE_WEAPON_GREATAXE : materials_greataxe,
            ITEM_SUB_TYPE_WEAPON_GREATMACE : materials_greatmace
        }
        
        materials_bow = [
           MATERIAL_WOOD 
        ]
        
        materials_crossbow = [
            MATERIAL_WOOD
        ]
        
        materials_boomerang = [
            MATERIAL_WOOD
        ]
        
        ranger_weapons = {
            ITEM_SUB_TYPE_WEAPON_BOW : materials_bow,
            ITEM_SUB_TYPE_WEAPON_CROSSBOW : materials_crossbow,
            ITEM_SUB_TYPE_WEAPON_BOOMERANG : materials_boomerang
        }
        
        materials_staff = [
            MATERIAL_WOOD
        ]
        
        materials_wand = [
            MATERIAL_WOOD
        ]
        
        materials_bracelet = [
            MATERIAL_SILVER,
            MATERIAL_GOLD,
        ]
        
        mage_weapons = {
            ITEM_SUB_TYPE_WEAPON_STAFF : materials_staff,
            ITEM_SUB_TYPE_WEAPON_WAND : materials_wand,
            ITEM_SUB_TYPE_WEAPON_BRACELET : materials_bracelet
        }
        
        materials_dagger = [
            MATERIAL_IRON
        ]
        
        materials_fist = [
            MATERIAL_IRON
        ]
        
        materials_longsword = [
            MATERIAL_IRON
        ]
        
        rogue_weapons = {
            ITEM_SUB_TYPE_WEAPON_DAGGER : materials_dagger,
            ITEM_SUB_TYPE_WEAPON_FIST : materials_fist,
            ITEM_SUB_TYPE_WEAPON_LONGSWORD : materials_longsword
        }
        
        weapons = {
            CLASS_WARRIOR : warrior_weapons,
            CLASS_RANGER : ranger_weapons,
            CLASS_MAGE : mage_weapons,
            CLASS_ROGUE : rogue_weapons
        }
        
        materials_warrior_armor = [
            MATERIAL_IRON
        ]
        
        warrior_armors = {
            ITEM_SUB_TYPE_ARMOR : materials_warrior_armor
        }
        
        materials_ranger_armor = [
            MATERIAL_LINEN
        ]
        
        ranger_armors = {
            ITEM_SUB_TYPE_ARMOR : materials_ranger_armor
        }
        
        materials_mage_armor = [
            MATERIAL_SILK
        ]
        
        mage_armors = {
            ITEM_SUB_TYPE_ARMOR : materials_mage_armor
        }
        
        materials_rogue_armor = [
            MATERIAL_COTTON
        ]
        
        rogue_armors = {
            ITEM_SUB_TYPE_ARMOR : materials_mage_armor
        }
        
        armors = {
            CLASS_WARRIOR : warrior_armors,
            CLASS_RANGER : ranger_armors,
            CLASS_MAGE : mage_armors,
            CLASS_ROGUE : rogue_armors
        }
        
        materials_warrior_gloves = [
            MATERIAL_IRON
        ]
        
        warrior_gloves = {
            ITEM_SUB_TYPE_GLOVES : materials_warrior_gloves
        }
        
        materials_ranger_gloves = [
            MATERIAL_LINEN
        ]
        
        ranger_gloves = {
            ITEM_SUB_TYPE_GLOVES : materials_ranger_gloves
        }
        
        materials_mage_gloves = [
            MATERIAL_SILK
        ]
        
        mage_gloves = {
            ITEM_SUB_TYPE_GLOVES : materials_mage_gloves
        }
        
        materials_rogue_gloves = [
            MATERIAL_COTTON
        ]

        rogue_gloves = {
            ITEM_SUB_TYPE_GLOVES : materials_rogue_gloves
        }
        
        gloves = {
            CLASS_WARRIOR : warrior_gloves,
            CLASS_RANGER : ranger_gloves,
            CLASS_MAGE : mage_gloves,
            CLASS_ROGUE : rogue_gloves
        }
        
        materials_warrior_boots = [
            MATERIAL_IRON
        ]
        
        warrior_boots = {
            ITEM_SUB_TYPE_BOOTS : materials_warrior_boots
        }
        
        materials_ranger_boots = [
            MATERIAL_LINEN
        ]
        
        ranger_boots = {
            ITEM_SUB_TYPE_BOOTS : materials_ranger_boots
        }
        
        materials_mage_boots = [
            MATERIAL_SILK
        ]
        
        mage_boots = {
            ITEM_SUB_TYPE_BOOTS : materials_mage_boots
        }
        
        materials_rogue_boots = [
            MATERIAL_COTTON
        ]

        rogue_boots = {
            ITEM_SUB_TYPE_BOOTS : materials_rogue_boots
        }
        
        boots = {
            CLASS_WARRIOR : warrior_boots,
            CLASS_RANGER : ranger_boots,
            CLASS_MAGE : mage_boots,
            CLASS_ROGUE : rogue_boots
        }
        
        materials_warrior_shoulder_armor = [
            MATERIAL_IRON
        ]
        
        warrior_shoulder_armors = {
            ITEM_SUB_TYPE_SHOULDER_ARMOR :
                materials_warrior_shoulder_armor
        }
        
        materials_ranger_shoulder_armor = [
            MATERIAL_LINEN
        ]
        
        ranger_shoulder_armors = {
            ITEM_SUB_TYPE_SHOULDER_ARMOR :
                materials_ranger_shoulder_armor
        }
        
        materials_mage_shoulder_armor = [
            MATERIAL_SILK
        ]
        
        mage_shoulder_armors = {
            ITEM_SUB_TYPE_SHOULDER_ARMOR :
                materials_mage_shoulder_armor
        }
        
        materials_rogue_shoulder_armor = [
            MATERIAL_COTTON
        ]

        rogue_shoulder_armors = {
            ITEM_SUB_TYPE_SHOULDER_ARMOR :
                materials_rogue_shoulder_armor
        }
        
        shoulder_armors = {
            CLASS_WARRIOR : warrior_shoulder_armors,
            CLASS_RANGER : ranger_shoulder_armors,
            CLASS_MAGE : mage_shoulder_armors,
            CLASS_ROGUE : rogue_shoulder_armors
        }
        
        materials_warrior_amulet = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        warrior_amulets = {
            ITEM_SUB_TYPE_AMULET : materials_warrior_amulet
        }
        
        materials_ranger_amulet = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        ranger_amulets = {
            ITEM_SUB_TYPE_AMULET : materials_ranger_amulet
        }
        
        materials_mage_amulet = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        mage_amulets = {
            ITEM_SUB_TYPE_AMULET : materials_mage_amulet
        }
        
        materials_rogue_amulet = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]

        rogue_amulets = {
            ITEM_SUB_TYPE_AMULET : materials_rogue_amulet
        }
        
        amulets = {
            CLASS_WARRIOR : warrior_amulets,
            CLASS_RANGER : ranger_amulets,
            CLASS_MAGE : mage_amulets,
            CLASS_ROGUE : rogue_amulets
        }
        
        materials_warrior_ring = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        warrior_rings = {
            ITEM_SUB_TYPE_RING : materials_warrior_ring
        }
        
        materials_ranger_ring = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        ranger_rings = {
            ITEM_SUB_TYPE_RING : materials_ranger_ring
        }
        
        materials_mage_ring = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]
        
        mage_rings = {
            ITEM_SUB_TYPE_RING : materials_mage_ring
        }
        
        materials_rogue_ring = [
            MATERIAL_GOLD,
            MATERIAL_SILVER
        ]

        rogue_rings = {
            ITEM_SUB_TYPE_AMULET : materials_rogue_ring
        }
        
        rings = {
            CLASS_WARRIOR : warrior_rings,
            CLASS_RANGER : ranger_rings,
            CLASS_MAGE : mage_rings,
            CLASS_ROGUE : rogue_rings
        }
        
        self.__item_materials = {
            ITEM_TYPE_WEAPON : weapons,
            ITEM_TYPE_ARMOR : armors,
            ITEM_TYPE_GLOVES : gloves,
            ITEM_TYPE_BOOTS : boots,
            ITEM_TYPE_SHOULDER_ARMOR : shoulder_armors,
            ITEM_TYPE_AMULET : amulets,
            ITEM_TYPE_RING : rings
        }
        