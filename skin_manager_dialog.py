import os
import sys
import json
import io
import base64
import requests
from PIL import Image
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QWidget, QLineEdit, QMessageBox, QFrame,
                             QFileDialog, QRadioButton, QButtonGroup,
                             QScrollArea, QGridLayout, QApplication, QComboBox,
                             QSizePolicy)
from PyQt6.QtGui import QIcon, QFont, QPixmap, QImage, QColor, QPainter
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView

from custom_window import CustomWindowMixin
from dialog_utils import show_warning, CustomMessageBox
from utils import resource_path

SKIN_CATALOG = {
    "Tutti": [
        # --- Classici & Leggende ---
        {"name": "Steve Classic",       "player": "Steve",             "variant": "classic", "category": "Classici",            "downloads": 98500, "popular": True,  "tags": ["steve", "classico", "default", "nostalgia"]},
        {"name": "Alex Classic",        "player": "Alex",              "variant": "slim",    "category": "Classici",            "downloads": 89200, "popular": True,  "tags": ["alex", "classico", "slim", "default", "girl"]},
        {"name": "Notch",               "player": "Notch",             "variant": "classic", "category": "Classici",            "downloads": 76400, "popular": True,  "tags": ["creator", "mojang", "notch", "leggenda"]},
        {"name": "Jeb_",                "player": "jeb_",              "variant": "classic", "category": "Classici",            "downloads": 58900, "popular": False, "tags": ["developer", "mojang", "jeb"]},
        {"name": "Dinnerbone",          "player": "Dinnerbone",        "variant": "classic", "category": "Classici",            "downloads": 64300, "popular": True,  "tags": ["mojang", "easteregg", "dinnerbone"]},
        {"name": "Grumm",               "player": "Grumm",             "variant": "slim",    "category": "Classici",            "downloads": 32100, "popular": False, "tags": ["mojang", "easteregg", "grumm"]},
        {"name": "Herobrine",           "player": "Herobrine",         "variant": "classic", "category": "Classici",            "downloads": 94100, "popular": True,  "tags": ["creepypasta", "herobrine", "dark", "horror", "boy"]},
        {"name": "Marc",                "player": "Marc",              "variant": "classic", "category": "Classici",            "downloads": 24000, "popular": False, "tags": ["mojang", "classici"]},

        # --- YouTuber & Creator ---
        {"name": "Technoblade",         "player": "Technoblade",       "variant": "classic", "category": "YouTuber & Creator",   "downloads": 128000, "popular": True, "tags": ["technoblade", "king", "pig", "pvp", "legend", "hoodie"]},
        {"name": "Dream",               "player": "Dream",             "variant": "classic", "category": "YouTuber & Creator",   "downloads": 115000, "popular": True, "tags": ["dream", "speedrun", "manhunt", "green", "boy"]},
        {"name": "DanTDM",              "player": "DanTDM",            "variant": "classic", "category": "YouTuber & Creator",   "downloads": 88000,  "popular": True, "tags": ["dantdm", "goggles", "blue", "creator", "boy"]},
        {"name": "Mumbo Jumbo",         "player": "MumboJumbo",        "variant": "classic", "category": "YouTuber & Creator",   "downloads": 67000,  "popular": True, "tags": ["mumbo", "redstone", "suit", "mustache", "boy"]},
        {"name": "Grian",               "player": "Grian",             "variant": "classic", "category": "YouTuber & Creator",   "downloads": 71000,  "popular": True, "tags": ["grian", "builder", "hermitcraft", "red", "boy"]},
        {"name": "TommyInnit",          "player": "TommyInnit",        "variant": "classic", "category": "YouTuber & Creator",   "downloads": 92000,  "popular": True, "tags": ["tommyinnit", "dsmp", "creator", "boy"]},
        {"name": "GeorgeNotFound",      "player": "GeorgeNotFound",    "variant": "classic", "category": "YouTuber & Creator",   "downloads": 84000,  "popular": True, "tags": ["george", "goggles", "blue", "dsmp", "boy"]},
        {"name": "Sapnap",              "player": "Sapnap",            "variant": "classic", "category": "YouTuber & Creator",   "downloads": 78000,  "popular": True, "tags": ["sapnap", "fire", "bandana", "pvp", "boy"]},
        {"name": "PewDiePie",           "player": "PewDiePie",         "variant": "classic", "category": "YouTuber & Creator",   "downloads": 96000,  "popular": True, "tags": ["pewdiepie", "youtube", "creator", "headphones"]},
        {"name": "Skeppy",              "player": "Skeppy",            "variant": "classic", "category": "YouTuber & Creator",   "downloads": 69000,  "popular": True, "tags": ["skeppy", "diamond", "blue", "boy"]},
        {"name": "BadBoyHalo",          "player": "BadBoyHalo",        "variant": "classic", "category": "YouTuber & Creator",   "downloads": 61000,  "popular": False, "tags": ["badboyhalo", "hoodie", "dark", "demon"]},
        {"name": "CaptainSparklez",     "player": "CaptainSparklez",   "variant": "classic", "category": "YouTuber & Creator",   "downloads": 75000,  "popular": True, "tags": ["captainsparklez", "fallenkingdom", "music", "boy"]},
        {"name": "Philza",              "player": "Philza",            "variant": "classic", "category": "YouTuber & Creator",   "downloads": 63000,  "popular": True, "tags": ["philza", "hardcore", "green", "wings", "anime"]},
        {"name": "Wilbur Soot",         "player": "WilburSoot",        "variant": "classic", "category": "YouTuber & Creator",   "downloads": 74000,  "popular": True, "tags": ["wilbur", "beanie", "music", "dsmp"]},
        {"name": "Ranboo",              "player": "Ranboo",            "variant": "slim",    "category": "YouTuber & Creator",   "downloads": 81000,  "popular": True, "tags": ["ranboo", "enderman", "suit", "crown", "boy"]},
        {"name": "Tubbo",               "player": "Tubbo",             "variant": "classic", "category": "YouTuber & Creator",   "downloads": 65000,  "popular": False, "tags": ["tubbo", "green", "dsmp", "boy"]},
        {"name": "Purpled",             "player": "Purpled",           "variant": "slim",    "category": "YouTuber & Creator",   "downloads": 79000,  "popular": True, "tags": ["purpled", "bedwars", "purple", "pvp", "hoodie"]},
        {"name": "xNestorio",           "player": "xNestorio",         "variant": "classic", "category": "YouTuber & Creator",   "downloads": 68000,  "popular": True, "tags": ["xnestorio", "uhc", "pvp", "archer", "boy"]},
        {"name": "Boffy",               "player": "Boffy",             "variant": "classic", "category": "YouTuber & Creator",   "downloads": 52000,  "popular": False, "tags": ["boffy", "comedy", "funny"]},
        {"name": "Karl Jacobs",         "player": "KarlJacobs",        "variant": "classic", "category": "YouTuber & Creator",   "downloads": 73000,  "popular": True, "tags": ["karljacobs", "hoodie", "colorful", "dsmp", "boy"]},
        {"name": "Quackity",            "player": "Quackity",          "variant": "classic", "category": "YouTuber & Creator",   "downloads": 82000,  "popular": True, "tags": ["quackity", "beanie", "suit", "duck", "boy"]},

        # --- PvP & Competitive ---
        {"name": "Sweat E-Boy",         "player": "Sweat",             "variant": "slim",    "category": "PvP & Competitive",   "downloads": 105000, "popular": True, "tags": ["pvp", "sweat", "boy", "hoodie", "black", "cool"]},
        {"name": "Shadow Ninja",        "player": "Ninja",             "variant": "slim",    "category": "PvP & Competitive",   "downloads": 97000,  "popular": True, "tags": ["ninja", "shadow", "pvp", "dark", "stealth", "black"]},
        {"name": "Knight Warrior",      "player": "Knight",            "variant": "classic", "category": "PvP & Competitive",   "downloads": 86000,  "popular": True, "tags": ["knight", "armor", "warrior", "pvp", "medieval"]},
        {"name": "Paladin Holy",        "player": "Paladin",           "variant": "classic", "category": "PvP & Competitive",   "downloads": 59000,  "popular": False, "tags": ["paladin", "gold", "armor", "fantasy", "pvp"]},
        {"name": "Cyber Samurai",       "player": "Samurai",           "variant": "classic", "category": "PvP & Competitive",   "downloads": 88000,  "popular": True, "tags": ["samurai", "cyberpunk", "katana", "pvp", "cool", "boy"]},
        {"name": "Assassin Hood",       "player": "Assassin",          "variant": "slim",    "category": "PvP & Competitive",   "downloads": 91000,  "popular": True, "tags": ["assassin", "hoodie", "pvp", "dark", "speed"]},
        {"name": "Dark Mage",           "player": "Mage",              "variant": "classic", "category": "PvP & Competitive",   "downloads": 64000,  "popular": False, "tags": ["mage", "magic", "purple", "fantasy", "pvp"]},
        {"name": "Ice Archer",          "player": "Archer",            "variant": "slim",    "category": "PvP & Competitive",   "downloads": 72000,  "popular": True, "tags": ["archer", "ice", "blue", "bow", "pvp", "girl"]},
        {"name": "Dragon Slayer",       "player": "DragonSlayer",      "variant": "classic", "category": "PvP & Competitive",   "downloads": 83000,  "popular": True, "tags": ["dragon", "slayer", "armor", "epic", "pvp"]},
        {"name": "Gladiator Champion",  "player": "Gladiator",         "variant": "classic", "category": "PvP & Competitive",   "downloads": 54000,  "popular": False, "tags": ["gladiator", "arena", "pvp", "warrior"]},
        {"name": "Valkyrie",            "player": "Valkyrie",          "variant": "slim",    "category": "PvP & Competitive",   "downloads": 77000,  "popular": True, "tags": ["valkyrie", "wings", "girl", "pvp", "gold", "warrior"]},
        {"name": "Ghost Hunter",        "player": "Ghost",             "variant": "slim",    "category": "PvP & Competitive",   "downloads": 69000,  "popular": False, "tags": ["ghost", "white", "pvp", "aesthetic", "dark"]},
        {"name": "Viking Berserk",      "player": "Viking",            "variant": "classic", "category": "PvP & Competitive",   "downloads": 61000,  "popular": False, "tags": ["viking", "nordic", "axe", "warrior"]},
        {"name": "Reaper Soul",         "player": "Reaper",            "variant": "classic", "category": "PvP & Competitive",   "downloads": 89000,  "popular": True, "tags": ["reaper", "death", "dark", "hoodie", "pvp", "black"]},

        # --- Anime & Pop Culture ---
        {"name": "Goku Super Saiyan",   "player": "Goku",              "variant": "classic", "category": "Anime & Pop Culture", "downloads": 112000, "popular": True, "tags": ["goku", "dragonball", "anime", "orange", "saiyan", "hero"]},
        {"name": "Naruto Uzumaki",      "player": "Naruto",            "variant": "classic", "category": "Anime & Pop Culture", "downloads": 104000, "popular": True, "tags": ["naruto", "ninja", "anime", "orange", "hero", "boy"]},
        {"name": "Sasuke Uchiha",       "player": "Sasuke",            "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 99000,  "popular": True, "tags": ["sasuke", "uchiha", "anime", "sharingan", "dark", "boy"]},
        {"name": "Monkey D. Luffy",     "player": "Luffy",             "variant": "classic", "category": "Anime & Pop Culture", "downloads": 108000, "popular": True, "tags": ["luffy", "onepiece", "anime", "strawhat", "pirate", "boy"]},
        {"name": "Roronoa Zoro",        "player": "Zoro",              "variant": "classic", "category": "Anime & Pop Culture", "downloads": 95000,  "popular": True, "tags": ["zoro", "onepiece", "anime", "swordsman", "green", "boy"]},
        {"name": "Levi Ackerman",       "player": "Levi",              "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 91000,  "popular": True, "tags": ["levi", "aot", "titan", "anime", "scout", "boy"]},
        {"name": "Tanjiro Kamado",      "player": "Tanjiro",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 87000,  "popular": True, "tags": ["tanjiro", "demonslayer", "anime", "katana", "boy"]},
        {"name": "Nezuko Kamado",       "player": "Nezuko",            "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 93000,  "popular": True, "tags": ["nezuko", "demonslayer", "anime", "kimono", "girl", "cute"]},
        {"name": "Gojo Satoru",         "player": "Gojo",              "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 120000, "popular": True, "tags": ["gojo", "jujutsukaisen", "anime", "blindfold", "cool", "boy"]},
        {"name": "Saitama One Punch",   "player": "Saitama",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 79000,  "popular": False, "tags": ["saitama", "onepunchman", "anime", "hero", "yellow"]},
        {"name": "Vegeta Prince",       "player": "Vegeta",            "variant": "classic", "category": "Anime & Pop Culture", "downloads": 82000,  "popular": True, "tags": ["vegeta", "dragonball", "anime", "blue", "saiyan"]},
        {"name": "Spider-Man",          "player": "Spiderman",         "variant": "classic", "category": "Anime & Pop Culture", "downloads": 109000, "popular": True, "tags": ["spiderman", "marvel", "superhero", "red", "hero"]},
        {"name": "Batman Dark Knight",  "player": "Batman",            "variant": "classic", "category": "Anime & Pop Culture", "downloads": 98000,  "popular": True, "tags": ["batman", "dc", "dark", "superhero", "black"]},
        {"name": "Iron Man Mark",       "player": "IronMan",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 86000,  "popular": True, "tags": ["ironman", "marvel", "armor", "superhero", "red"]},
        {"name": "Deadpool",            "player": "Deadpool",          "variant": "classic", "category": "Anime & Pop Culture", "downloads": 92000,  "popular": True, "tags": ["deadpool", "marvel", "red", "humor", "superhero"]},
        {"name": "Link (Zelda)",        "player": "Link",              "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 74000,  "popular": True, "tags": ["link", "zelda", "nintendo", "green", "fantasy"]},
        {"name": "Sonic The Hedgehog",  "player": "Sonic",             "variant": "classic", "category": "Anime & Pop Culture", "downloads": 76000,  "popular": False, "tags": ["sonic", "sega", "blue", "speed", "animal"]},
        {"name": "Super Mario",         "player": "Mario",             "variant": "classic", "category": "Anime & Pop Culture", "downloads": 73000,  "popular": False, "tags": ["mario", "nintendo", "red", "game"]},
        {"name": "Pikachu Hood",        "player": "Pikachu",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 89000,  "popular": True, "tags": ["pikachu", "pokemon", "yellow", "cute", "anime"]},
        {"name": "Kirby Cute",          "player": "Kirby",             "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 67000,  "popular": False, "tags": ["kirby", "nintendo", "pink", "cute"]},

        # --- Mob & Creature ---
        {"name": "Enderman Suit",       "player": "Enderman",          "variant": "classic", "category": "Mob & Creature",      "downloads": 99000,  "popular": True, "tags": ["enderman", "mob", "ender", "purple", "black", "suit"]},
        {"name": "Creeper Hoodie",      "player": "Creeper",           "variant": "classic", "category": "Mob & Creature",      "downloads": 97000,  "popular": True, "tags": ["creeper", "mob", "green", "hoodie", "boom"]},
        {"name": "Zombie Survival",     "player": "Zombie",            "variant": "classic", "category": "Mob & Creature",      "downloads": 68000,  "popular": False, "tags": ["zombie", "mob", "undead", "green"]},
        {"name": "Skeleton Sniper",     "player": "Skeleton",          "variant": "classic", "category": "Mob & Creature",      "downloads": 65000,  "popular": False, "tags": ["skeleton", "mob", "undead", "bow", "gray"]},
        {"name": "Piglin Gold",         "player": "Piglin",            "variant": "classic", "category": "Mob & Creature",      "downloads": 62000,  "popular": False, "tags": ["piglin", "nether", "gold", "mob"]},
        {"name": "Blaze Fire",          "player": "Blaze",             "variant": "classic", "category": "Mob & Creature",      "downloads": 63000,  "popular": False, "tags": ["blaze", "fire", "nether", "yellow", "mob"]},
        {"name": "Witch Alchemist",     "player": "Witch",             "variant": "slim",    "category": "Mob & Creature",      "downloads": 58000,  "popular": False, "tags": ["witch", "magic", "potion", "hat", "girl"]},
        {"name": "Wither Skeleton",     "player": "WitherSkeleton",    "variant": "classic", "category": "Mob & Creature",      "downloads": 71000,  "popular": True, "tags": ["wither", "skeleton", "nether", "dark", "sword"]},
        {"name": "Iron Golem Knight",   "player": "IronGolem",         "variant": "classic", "category": "Mob & Creature",      "downloads": 66000,  "popular": False, "tags": ["irongolem", "golem", "armor", "village", "strong"]},
        {"name": "Phantom Shadow",      "player": "Phantom",           "variant": "slim",    "category": "Mob & Creature",      "downloads": 59000,  "popular": False, "tags": ["phantom", "wings", "blue", "night", "dark"]},
        {"name": "Ender Dragon Human",  "player": "EnderDragon",       "variant": "slim",    "category": "Mob & Creature",      "downloads": 94000,  "popular": True, "tags": ["enderdragon", "dragon", "wings", "purple", "dark", "cool"]},
        {"name": "Warden Deep",         "player": "Warden",            "variant": "classic", "category": "Mob & Creature",      "downloads": 87000,  "popular": True, "tags": ["warden", "sculk", "deepdark", "blue", "monster"]},

        # --- Aesthetic, Boy & Girl ---
        {"name": "Aesthetic Pastel",    "player": "Pastel",            "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 102000, "popular": True, "tags": ["pastel", "aesthetic", "cute", "girl", "soft", "pink"]},
        {"name": "Cyberpunk Neon",      "player": "Cyber",             "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 96000,  "popular": True, "tags": ["cyberpunk", "neon", "cyan", "cool", "boy", "future"]},
        {"name": "Cat Girl Maid",       "player": "Neko",              "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 107000, "popular": True, "tags": ["neko", "catgirl", "maid", "cute", "girl", "anime"]},
        {"name": "Hoodie Bear Chill",   "player": "Bear",              "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 89000,  "popular": True, "tags": ["bear", "hoodie", "aesthetic", "cozy", "cute", "boy"]},
        {"name": "Demon Horns Boy",     "player": "Demon",             "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 94000,  "popular": True, "tags": ["demon", "horns", "dark", "red", "boy", "hoodie"]},
        {"name": "Angel Divine Girl",   "player": "Angel",             "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 92000,  "popular": True, "tags": ["angel", "halo", "wings", "white", "girl", "cute"]},
        {"name": "Galaxy Space Traveler","player": "Galaxy",           "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 98000,  "popular": True, "tags": ["galaxy", "stars", "purple", "space", "cool"]},
        {"name": "Astronaut Lunar",     "player": "Astronaut",         "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 75000,  "popular": False, "tags": ["astronaut", "space", "suit", "white"]},
        {"name": "Duck Outfit Cute",    "player": "Duck",              "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 81000,  "popular": True, "tags": ["duck", "yellow", "cute", "fun", "costume"]},
        {"name": "Frog Hat Aesthetic",  "player": "Frog",              "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 84000,  "popular": True, "tags": ["frog", "green", "cute", "aesthetic", "girl"]},
        {"name": "Wizard Starry Night", "player": "Wizard",            "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 71000,  "popular": False, "tags": ["wizard", "magic", "stars", "blue", "fantasy"]},
        {"name": "Pirate Captain",      "player": "Pirate",            "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 67000,  "popular": False, "tags": ["pirate", "sea", "hat", "eyepatch", "boy"]},
        {"name": "Fire Demon Knight",   "player": "FireKnight",        "variant": "classic", "category": "PvP & Competitive",   "downloads": 85000,  "popular": True, "tags": ["fire", "knight", "red", "pvp", "warrior", "dark"]},
        {"name": "Toxic Hazard Bio",    "player": "Hazard",            "variant": "classic", "category": "PvP & Competitive",   "downloads": 76000,  "popular": False, "tags": ["toxic", "hazard", "green", "pvp", "hoodie"]},
        {"name": "Samurai Oni Red",     "player": "Oni",               "variant": "classic", "category": "Anime & Pop Culture", "downloads": 93000,  "popular": True, "tags": ["oni", "mask", "red", "samurai", "anime", "demon"]},
        {"name": "Megumin Explosion",   "player": "Megumin",           "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 89000,  "popular": True, "tags": ["megumin", "konosuba", "anime", "wizard", "hat", "girl"]},
        {"name": "Kakashi Hatake",      "player": "Kakashi",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 103000, "popular": True, "tags": ["kakashi", "naruto", "ninja", "anime", "sharingan", "cool"]},
        {"name": "E-Girl Pink Beanie",  "player": "Egirl",             "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 106000, "popular": True, "tags": ["egirl", "pink", "beanie", "aesthetic", "cute", "girl"]},
        {"name": "Fox Girl Cozy",       "player": "FoxGirl",           "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 95000,  "popular": True, "tags": ["fox", "cute", "ears", "orange", "girl", "aesthetic"]},
        {"name": "Wolf Boy Hoodie",     "player": "WolfBoy",           "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 97000,  "popular": True, "tags": ["wolf", "ears", "hoodie", "boy", "aesthetic", "grey"]},
        {"name": "Axolotl Pink Cute",   "player": "Axolotl",           "variant": "slim",    "category": "Mob & Creature",      "downloads": 99000,  "popular": True, "tags": ["axolotl", "pink", "cute", "mob", "water"]},
        {"name": "Bee Outfit Honey",    "player": "Bee",               "variant": "slim",    "category": "Mob & Creature",      "downloads": 88000,  "popular": True, "tags": ["bee", "honey", "yellow", "cute", "mob", "wings"]},
        {"name": "Slime Boy Green",     "player": "Slime",             "variant": "classic", "category": "Mob & Creature",      "downloads": 86000,  "popular": True, "tags": ["slime", "green", "cute", "mob", "boy"]},
        {"name": "Goth Dark Aesthetic", "player": "Goth",              "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 94000,  "popular": True, "tags": ["goth", "black", "dark", "aesthetic", "girl"]},
        {"name": "Cactus Desert Man",   "player": "Cactus",            "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 64000,  "popular": False, "tags": ["cactus", "green", "funny", "costume"]},
        {"name": "Neon DJ Music",       "player": "DJ",                "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 81000,  "popular": False, "tags": ["dj", "headphones", "music", "neon", "cool"]},
        {"name": "Cyber Girl Hologram", "player": "Holo",              "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 89000,  "popular": True, "tags": ["cyber", "hologram", "cyan", "girl", "future"]},
        {"name": "Steampunk Aviator",   "player": "Steampunk",         "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 72000,  "popular": False, "tags": ["steampunk", "goggles", "brown", "gear", "cool"]},
        {"name": "Snow Winter Cozy",    "player": "Winter",            "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 79000,  "popular": False, "tags": ["winter", "snow", "scarf", "white", "girl"]},
        {"name": "Darth Vader Dark",    "player": "Vader",             "variant": "classic", "category": "Anime & Pop Culture", "downloads": 99000,  "popular": True, "tags": ["starwars", "vader", "dark", "sith", "black", "villain"]},
        {"name": "Yoda Jedi Master",    "player": "Yoda",              "variant": "classic", "category": "Anime & Pop Culture", "downloads": 75000,  "popular": False, "tags": ["starwars", "yoda", "green", "jedi"]},
        {"name": "Master Chief Spartan","player": "MasterChief",       "variant": "classic", "category": "Anime & Pop Culture", "downloads": 91000,  "popular": True, "tags": ["halo", "masterchief", "green", "armor", "hero", "game"]},
        {"name": "Doom Slayer Marine",  "player": "Doomguy",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 94000,  "popular": True, "tags": ["doom", "doomguy", "armor", "green", "action"]},
        {"name": "Kratos God of War",   "player": "Kratos",            "variant": "classic", "category": "Anime & Pop Culture", "downloads": 96000,  "popular": True, "tags": ["kratos", "godofwar", "warrior", "red", "action"]},
        {"name": "Geralt of Rivia",     "player": "Witcher",           "variant": "classic", "category": "Anime & Pop Culture", "downloads": 88000,  "popular": True, "tags": ["witcher", "geralt", "sword", "fantasy", "white"]},
        {"name": "Panda Hoodie Relax",  "player": "Panda",             "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 92000,  "popular": True, "tags": ["panda", "hoodie", "black", "white", "cute", "animal"]},
        {"name": "Koala Boy Cute",      "player": "Koala",             "variant": "classic", "category": "Aesthetic & Casual",  "downloads": 73000,  "popular": False, "tags": ["koala", "cute", "grey", "animal", "boy"]},
        {"name": "Devil Demon Girl",    "player": "DevilGirl",         "variant": "slim",    "category": "Aesthetic & Casual",  "downloads": 98000,  "popular": True, "tags": ["devil", "horns", "red", "girl", "dark", "cute"]},
        {"name": "Sailor Moon Magical", "player": "SailorMoon",        "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 89000,  "popular": True, "tags": ["sailormoon", "anime", "magic", "blonde", "girl"]},
        {"name": "Hatsune Miku Idol",   "player": "Miku",              "variant": "slim",    "category": "Anime & Pop Culture", "downloads": 110000, "popular": True, "tags": ["miku", "vocaloid", "anime", "cyan", "twintails", "girl"]},
    ]
}

def resolve_mojang_skin(identifier):
    """
    Risolve username o UUID Java su Mojang API per ottenere:
    (skin_bytes, variant, resolved_name, resolved_uuid)
    """
    clean_id = identifier.strip()
    uuid_clean = clean_id.replace("-", "")
    player_name = clean_id

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # Se non è un UUID di 32 cifre esadecimali, risolviamo il nome giocatore in UUID
    if not (len(uuid_clean) == 32 and all(c in "0123456789abcdefABCDEF" for c in uuid_clean)):
        url_profile = f"https://api.mojang.com/users/profiles/minecraft/{clean_id}"
        r = requests.get(url_profile, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            uuid_clean = data.get("id", "")
            player_name = data.get("name", clean_id)
        elif r.status_code == 404:
            raise ValueError(f"Nessun giocatore Minecraft trovato con il nome '{clean_id}'.")
        else:
            raise RuntimeError(f"Errore Mojang API ({r.status_code}) nella ricerca del nome.")

    if not uuid_clean:
        raise ValueError("Impossibile determinare l'UUID del giocatore.")

    session_url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid_clean}"
    r_session = requests.get(session_url, headers=headers, timeout=6)
    if r_session.status_code != 200:
        raise RuntimeError(f"Impossibile ottenere i dati della skin da Mojang ({r_session.status_code}).")

    session_data = r_session.json()
    player_name = session_data.get("name", player_name)
    properties = session_data.get("properties", [])
    
    skin_url = None
    variant = "classic"

    for prop in properties:
        if prop.get("name") == "textures":
            raw_val = prop.get("value", "")
            decoded = base64.b64decode(raw_val).decode('utf-8')
            parsed_textures = json.loads(decoded)
            skin_obj = parsed_textures.get("textures", {}).get("SKIN", {})
            skin_url = skin_obj.get("url")
            meta = skin_obj.get("metadata", {})
            if meta.get("model") == "slim":
                variant = "slim"
            break

    if not skin_url:
        raise ValueError(f"Nessuna skin personalizzata trovata per {player_name}.")

    r_skin = requests.get(skin_url, headers=headers, timeout=8)
    if r_skin.status_code != 200 or len(r_skin.content) < 100:
        raise RuntimeError("Download della texture della skin fallito.")

    return r_skin.content, variant, player_name, uuid_clean


class PlayerSearchWorker(QObject):
    """Worker per ricercare un giocatore o skin online tramite Mineskin search o Mojang API."""
    finished = pyqtSignal(bytes, str, str)  # skin_bytes, variant, display_name
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        query_clean = self.query.strip()
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        # 1. Tentativo prioritario su Mojang Session Server (username Minecraft Java ufficiale)
        try:
            skin_bytes, variant, player_name, _ = resolve_mojang_skin(query_clean)
            self.finished.emit(skin_bytes, variant, player_name)
            return
        except Exception:
            pass

        # 2. Fallback su Mineskin v2 Search API (per nome o shortId)
        try:
            search_url = f"https://api.mineskin.org/v2/skins?search={query_clean}"
            r_search = requests.get(search_url, headers=headers, timeout=8)
            if r_search.status_code == 200:
                data = r_search.json()
                skins = data.get("skins", [])
                if skins:
                    s = skins[0]
                    short_id = s.get("shortId")
                    uuid_val = s.get("uuid")
                    identifier = short_id or uuid_val
                    if identifier:
                        r_api = requests.get(f"https://api.mineskin.org/v2/skins/{identifier}", headers=headers, timeout=8)
                        if r_api.status_code == 200:
                            api_data = r_api.json()
                            skin_data = api_data.get("skin", {})
                            variant = skin_data.get("variant", "classic")
                            texture_data = skin_data.get("texture", {}).get("data", {}).get("value")
                            if texture_data:
                                decoded_json = json.loads(base64.b64decode(texture_data).decode('utf-8'))
                                skin_url = decoded_json.get("textures", {}).get("SKIN", {}).get("url")
                                if skin_url:
                                    r_skin = requests.get(skin_url, headers=headers, timeout=8)
                                    if r_skin.status_code == 200 and len(r_skin.content) > 100:
                                        self.finished.emit(r_skin.content, variant, query_clean)
                                        return
        except Exception as e:
            self.error.emit(str(e))
            return

        self.error.emit(f"Nessun giocatore o skin trovata per '{query_clean}'.")


class MineskinCatalogWorker(QObject):
    """Worker per filtrare e ricercare nel catalogo con tag, popolarità e categorie,
    con navigazione paginata online su Mineskin v2 per migliaia di skin."""
    finished = pyqtSignal(list, int)  # items_for_page, total_count
    error = pyqtSignal(str)

    MINESKIN_TOTAL_ESTIMATE = 5000  # stima conservativa del totale online

    def __init__(self, page=1, size=9, search_query="", category="Tutte", sort_by="popolari", tag=""):
        super().__init__()
        self.page = page
        self.size = size
        self.search_query = search_query.strip().lower()
        self.category = category
        self.sort_by = sort_by
        self.tag = tag.strip().lower()

    def _is_online_mode(self):
        """Modalità online: nessun filtro attivo → navigazione Mineskin v2."""
        return (not self.search_query
                and not self.tag
                and (self.category == "Tutte" or self.category == "Tutte le Categorie"))

    def _fetch_online(self):
        """Recupera skin dalla Mineskin v2 API con paginazione server-side."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f"https://api.mineskin.org/v2/skins?size={self.size}&page={self.page}"

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                return [], self.MINESKIN_TOTAL_ESTIMATE

            data = res.json()
            skins_raw = data.get("skins", [])

            # Prova a leggere il totale dall'API
            pagination = data.get("pagination", {})
            total = pagination.get("total") or pagination.get("count")
            if not total or total < 100:
                total = self.MINESKIN_TOTAL_ESTIMATE

            items = []
            seen = set()
            for s in skins_raw:
                short_id = s.get("shortId") or s.get("id")
                uuid_val = s.get("uuid")
                texture_hash = (s.get("texture") or {}).get("hash") if isinstance(s.get("texture"), dict) else s.get("texture")
                p_name = s.get("name") or s.get("displayName")
                key = short_id or uuid_val or texture_hash
                if not key or key in seen:
                    continue
                seen.add(key)
                variant = s.get("variant") or "classic"
                items.append({
                    "name": p_name or f"Skin {short_id or '?'}",
                    "player": uuid_val or p_name or short_id or "",
                    "shortId": short_id,
                    "texture": texture_hash,
                    "variant": variant,
                    "category": "Libreria Online",
                    "downloads": 0,
                    "popular": False,
                    "tags": ["online"]
                })

            return items, int(total)
        except Exception:
            return [], 0

    def _fetch_search(self):
        """Cerca sia nel catalogo locale che online su Mineskin v2."""
        all_catalog = list(SKIN_CATALOG.get("Tutti", []))
        filtered = []

        for item in all_catalog:
            cat = item.get("category", "")

            # Filtro Categoria
            if self.category and self.category not in ("Tutte", "Tutte le Categorie"):
                if cat != self.category:
                    continue

            # Filtro Tag
            tags = [t.lower() for t in item.get("tags", [])]
            if self.tag and self.tag not in tags:
                continue

            # Filtro Ricerca Query
            if self.search_query:
                q = self.search_query
                match = (q in item.get("name", "").lower()
                         or q in item.get("player", "").lower()
                         or any(q in t for t in tags)
                         or q in cat.lower())
                if not match:
                    continue

            filtered.append(dict(item))

        # Ordinamento locale
        if self.sort_by == "scaricate":
            filtered.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        elif self.sort_by == "popolari":
            filtered.sort(key=lambda x: (x.get("popular", False), x.get("downloads", 0)), reverse=True)
        elif self.sort_by == "az":
            filtered.sort(key=lambda x: x.get("name", "").lower())

        # Se la ricerca non trova risultati locali, cerca su Mineskin online
        if not filtered and self.search_query:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            url = f"https://api.mineskin.org/v2/skins?size=40&search={self.search_query}"
            try:
                res_s = requests.get(url, headers=headers, timeout=8)
                if res_s.status_code == 200:
                    s_data = res_s.json()
                    for s in s_data.get("skins", []):
                        short_id = s.get("shortId") or s.get("id")
                        uuid_val = s.get("uuid")
                        texture_hash = (s.get("texture") or {}).get("hash") if isinstance(s.get("texture"), dict) else s.get("texture")
                        p_name = s.get("name") or s.get("displayName")
                        if not (short_id or uuid_val):
                            continue
                        filtered.append({
                            "name": p_name or f"Skin {short_id or '?'}",
                            "player": uuid_val or p_name or short_id or "",
                            "shortId": short_id,
                            "texture": texture_hash,
                            "variant": s.get("variant", "classic"),
                            "category": "Libreria Online",
                            "downloads": 0,
                            "popular": False,
                            "tags": ["online"]
                        })
            except Exception:
                pass

            # Fallback nome giocatore Mojang
            if not filtered and len(self.search_query) <= 16 and " " not in self.search_query:
                filtered.append({
                    "name": f"Giocatore: {self.search_query}",
                    "player": self.search_query,
                    "shortId": None,
                    "texture": None,
                    "variant": "classic",
                    "category": "Cerca Giocatore",
                    "downloads": 0,
                    "popular": False,
                    "tags": ["player"]
                })

        total_count = len(filtered)
        start_idx = (self.page - 1) * self.size
        page_items = filtered[start_idx:start_idx + self.size]
        return page_items, total_count

    def run(self):
        try:
            if self._is_online_mode():
                items, total = self._fetch_online()
            else:
                items, total = self._fetch_search()
            self.finished.emit(items, total)
        except Exception as e:
            self.error.emit(str(e))


class ThumbnailWorker(QObject):
    """Worker in background per scaricare la miniatura render del corpo o della testa di una skin."""
    thumbnail_ready = pyqtSignal(str, QPixmap)

    def __init__(self, item_id, item_data):
        super().__init__()
        self.item_id = item_id
        if isinstance(item_data, dict):
            self.item_data = item_data
        else:
            self.item_data = {"player": item_data}

    def run(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        player_name = self.item_data.get("player")
        short_id = self.item_data.get("shortId")
        texture_hash = self.item_data.get("texture")

        # 1. Tentativo con il render di mc-heads.net e minotar
        render_urls = []
        if texture_hash:
            render_urls.append(f"https://mc-heads.net/body/{texture_hash}/100")
        if short_id:
            render_urls.append(f"https://mc-heads.net/body/{short_id}/100")
        if player_name:
            render_urls.append(f"https://mc-heads.net/body/{player_name}/100")
            render_urls.append(f"https://minotar.net/armor/body/{player_name}/100.png")

        for r_url in render_urls:
            try:
                res = requests.get(r_url, headers=headers, timeout=5)
                if res.status_code == 200 and len(res.content) > 100:
                    pix = QPixmap()
                    if pix.loadFromData(res.content) and not pix.isNull():
                        self.thumbnail_ready.emit(self.item_id, pix)
                        return
            except Exception:
                continue

        # 2. Fallback: Se abbiamo il texture hash, usiamo il nostro render 2D
        if texture_hash:
            try:
                mojang_url = f"https://textures.minecraft.net/texture/{texture_hash}"
                res = requests.get(mojang_url, headers=headers, timeout=5)
                if res.status_code == 200 and len(res.content) > 100:
                    skin_img = Image.open(io.BytesIO(res.content)).convert('RGBA')
                    
                    body = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
                    head = Image.alpha_composite(skin_img.crop((8, 8, 16, 16)), skin_img.crop((40, 8, 48, 16)))
                    body.paste(head, (4, 0))
                    
                    torso = Image.alpha_composite(skin_img.crop((20, 20, 28, 32)), skin_img.crop((20, 36, 28, 48)))
                    body.paste(torso, (4, 8))
                    
                    r_arm = Image.alpha_composite(skin_img.crop((44, 20, 48, 32)), skin_img.crop((44, 36, 48, 48)))
                    body.paste(r_arm, (0, 8))
                    
                    if skin_img.height >= 64:
                        l_arm = Image.alpha_composite(skin_img.crop((36, 52, 40, 64)), skin_img.crop((52, 52, 56, 64)))
                    else:
                        l_arm = r_arm.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    body.paste(l_arm, (12, 8))
                    
                    r_leg = Image.alpha_composite(skin_img.crop((4, 20, 8, 32)), skin_img.crop((4, 36, 8, 48)))
                    body.paste(r_leg, (4, 20))
                    
                    if skin_img.height >= 64:
                        l_leg = Image.alpha_composite(skin_img.crop((20, 52, 24, 64)), skin_img.crop((4, 52, 8, 64)))
                    else:
                        l_leg = r_leg.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    body.paste(l_leg, (8, 20))

                    preview = body.resize((50, 100), Image.Resampling.NEAREST)
                    out_bytes = io.BytesIO()
                    preview.save(out_bytes, format='PNG')
                    
                    pix = QPixmap()
                    if pix.loadFromData(out_bytes.getvalue()) and not pix.isNull():
                        self.thumbnail_ready.emit(self.item_id, pix)
                        return
            except Exception:
                pass


class SkinDownloadWorker(QObject):
    """Scarica la texture di un elemento del catalogo."""
    finished = pyqtSignal(bytes, str, str)
    error = pyqtSignal(str)

    def __init__(self, item):
        super().__init__()
        self.item = item

    def run(self):
        short_id = self.item.get("shortId")
        player = self.item.get("player", "")
        texture_hash = self.item.get("texture")
        variant = self.item.get("variant", "classic")
        name = self.item.get("name", player or "Skin")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        # 1. Se abbiamo il texture hash diretto di Mojang
        if texture_hash:
            try:
                mojang_url = f"https://textures.minecraft.net/texture/{texture_hash}"
                r_tex = requests.get(mojang_url, headers=headers, timeout=6)
                if r_tex.status_code == 200 and len(r_tex.content) > 100:
                    self.finished.emit(r_tex.content, variant, name)
                    return
            except Exception:
                pass

        # 2. Se è un elemento Mineskin (v2 API)
        if short_id or (player and len(player) == 32 and "-" not in player):
            identifier = short_id or player
            try:
                r_api = requests.get(f"https://api.mineskin.org/v2/skins/{identifier}", headers=headers, timeout=8)
                if r_api.status_code == 200:
                    data = r_api.json()
                    skin_data = data.get("skin", {})
                    api_variant = skin_data.get("variant", variant)
                    texture_data = skin_data.get("texture", {}).get("data", {}).get("value")
                    if texture_data:
                        decoded_json = json.loads(base64.b64decode(texture_data).decode('utf-8'))
                        skin_url = decoded_json.get("textures", {}).get("SKIN", {}).get("url")
                        if skin_url:
                            r_skin = requests.get(skin_url, headers=headers, timeout=8)
                            if r_skin.status_code == 200 and len(r_skin.content) > 100:
                                self.finished.emit(r_skin.content, api_variant, name)
                                return
            except Exception:
                pass

        if player and len(player) != 32:
            try:
                skin_bytes, mojang_variant, _, _ = resolve_mojang_skin(player)
                chosen_variant = mojang_variant or variant
                self.finished.emit(skin_bytes, chosen_variant, name)
                return
            except Exception:
                pass

        fallback_queries = [short_id, player]
        for q in filter(None, fallback_queries):
            urls = [
                f"https://minotar.net/skin/{q}",
                f"https://mc-heads.net/skin/{q}",
                f"https://crafatar.com/skins/{q}"
            ]
            for u in urls:
                try:
                    r = requests.get(u, headers=headers, timeout=5)
                    if r.status_code == 200 and len(r.content) > 100:
                        self.finished.emit(r.content, variant, name)
                        return
                except Exception:
                    continue

        self.error.emit(f"Impossibile scaricare la skin per '{name}'.")


class SkinManagerDialog(QDialog, CustomWindowMixin):
    """
    Finestra moderna di gestione e scelta skin per account Microsoft:
    - Ricerca per giocatore / creator Minecraft
    - Catalogo online organizzato per categorie e paginato
    - Anteprima 3D in tempo reale con rotazione e animazione
    - Modelli Steve (Classic) e Alex (Slim)
    - Esportazione PNG locale e caricamento file PNG
    - Applicazione all'account con rinnovo token automatico
    """

    def __init__(self, parent, account, account_manager=None, client_id="", client_secret=""):
        super().__init__(parent)
        self.account = account
        self.account_manager = account_manager
        self.client_id = client_id
        self.client_secret = client_secret

        self.current_skin_bytes = None
        self.current_model = "classic"
        self.current_anim = "walk"
        self.current_page = 1
        self.page_size = 9
        self.total_items_count = 0
        self.active_category = "Tutte"
        self.active_sort = "popolari"
        self.active_tag = ""
        self.search_query = ""
        self.filtered_skins = []

        # Cache delle pagine caricate per garantire stabilità nel back/forward (divisa per query di ricerca)
        self.pages_cache = {}

        self.card_labels = {}
        self.card_threads = []
        self.card_workers = []
        self.active_threads = []
        self.skin_download_thread = None
        self.skin_viewer_ready = False

        self.skinview3d_js = self.load_local_skinview3d()

        self.setupUi()
        self.apply_stylesheet()

        self.load_account_current_skin()
        self.load_catalog_page(1)

    def closeEvent(self, event):
        if self.skin_download_thread and self.skin_download_thread.isRunning():
            self.skin_download_thread.quit()
            self.skin_download_thread.wait(500)
        for thread in self.active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait(500)
        for thread in self.card_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait(500)
        super().closeEvent(event)

    def load_local_skinview3d(self):
        js_path = resource_path("assets/skinview3d.bundle.js")
        if os.path.exists(js_path):
            try:
                with open(js_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def setupUi(self):
        username = self.account.get('username', 'Giocatore')
        self.setWindowTitle(f"Gestione Skin — {username}")
        self.setMinimumSize(1100, 740)
        self.resize(1140, 760)

        self.init_custom_frame(title=f"Gestione Skin — {username}", icon=self.windowIcon(), show_maximize=False)

        main_layout = self.content_layout
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        splitter = QHBoxLayout()
        splitter.setSpacing(16)

        # ==========================================
        # COLONNA SINISTRA: ANTEPRIMA 3D & CONTROLLI
        # ==========================================
        left_panel = QFrame()
        left_panel.setObjectName("PreviewCard")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_title = QLabel("<b>Anteprima 3D Interattiva</b>")
        preview_title.setStyleSheet("color: #f8fafc; font-size: 11pt;")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()

        self.skin_name_badge = QLabel("In uso")
        self.skin_name_badge.setStyleSheet("color: #38bdf8; font-size: 8.5pt; font-weight: bold; background: #1e293b; padding: 2px 8px; border-radius: 4px;")
        preview_header.addWidget(self.skin_name_badge)
        left_layout.addLayout(preview_header)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(320, 400)
        self.web_view.setStyleSheet("background: #101216; border-radius: 8px;")
        self.web_view.page().setBackgroundColor(QColor("#101216"))
        left_layout.addWidget(self.web_view, 1)

        # Modello Steve / Alex
        model_box = QHBoxLayout()
        model_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_box.setSpacing(16)

        self.model_group = QButtonGroup(self)
        self.radio_classic = QRadioButton("Classico (Steve 4px)")
        self.radio_slim = QRadioButton("Slim (Alex 3px)")
        self.radio_classic.setChecked(True)
        self.model_group.addButton(self.radio_classic, 0)
        self.model_group.addButton(self.radio_slim, 1)

        self.radio_classic.toggled.connect(self.on_model_changed)
        self.radio_slim.toggled.connect(self.on_model_changed)

        model_box.addWidget(self.radio_classic)
        model_box.addWidget(self.radio_slim)
        left_layout.addLayout(model_box)

        # Controlli Animazione
        anim_layout = QHBoxLayout()
        anim_layout.setSpacing(6)
        anim_lbl = QLabel("Animazione:")
        anim_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        anim_layout.addWidget(anim_lbl)

        self.anim_combo = QComboBox()
        self.anim_combo.addItems(["Camminata", "Corsa", "Fermo (Idle)"])
        self.anim_combo.currentIndexChanged.connect(self.on_anim_changed)
        anim_layout.addWidget(self.anim_combo, 1)

        self.btn_export_png = QPushButton("Salva PNG")
        self.btn_export_png.setObjectName("SecondaryButtonSmall")
        self.btn_export_png.setToolTip("Salva la texture PNG corrente sul computer")
        self.btn_export_png.clicked.connect(self.export_current_skin_png)
        anim_layout.addWidget(self.btn_export_png)

        left_layout.addLayout(anim_layout)
        splitter.addWidget(left_panel, 0)

        # ==========================================
        # COLONNA DESTRA: CATALOGO & RICERCA ONLINE
        # ==========================================
        right_panel = QFrame()
        right_panel.setObjectName("SidebarCard")
        right_panel.setMinimumWidth(420)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        # Barra superiore: Titolo e Pulsante file locale
        top_bar = QHBoxLayout()
        lib_title = QLabel("<b>Catalogo Skin & Tendenze</b>")
        lib_title.setStyleSheet("color: #f8fafc; font-size: 11pt;")
        top_bar.addWidget(lib_title)
        top_bar.addStretch()

        self.btn_browse = QPushButton("Carica File PNG...")
        self.btn_browse.setObjectName("SecondaryButton")
        self.btn_browse.clicked.connect(self.browse_local_skin)
        top_bar.addWidget(self.btn_browse)
        right_layout.addLayout(top_bar)

        # Barra filtri: Categoria + Ordinamento (Popolari, Scaricate, A-Z)
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems([
            "Tutte le Categorie",
            "Classici",
            "YouTuber & Creator",
            "PvP & Competitive",
            "Anime & Pop Culture",
            "Mob & Creature",
            "Aesthetic & Casual"
        ])
        self.cat_combo.currentTextChanged.connect(self.on_category_changed)
        filter_bar.addWidget(self.cat_combo, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Piu Popolari", "popolari")
        self.sort_combo.addItem("Piu Scaricate", "scaricate")
        self.sort_combo.addItem("Dalla A alla Z", "az")
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        filter_bar.addWidget(self.sort_combo, 1)

        right_layout.addLayout(filter_bar)

        # Barra Tag Rapidi (Pills cliccabili senza emoji)
        tags_scroll = QScrollArea()
        tags_scroll.setFixedHeight(38)
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tags_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        tags_container = QWidget()
        tags_layout = QHBoxLayout(tags_container)
        tags_layout.setContentsMargins(0, 2, 0, 2)
        tags_layout.setSpacing(6)

        popular_tags = [
            ("Tutti i Tag", ""),
            ("PvP", "pvp"),
            ("Anime", "anime"),
            ("Boy", "boy"),
            ("Girl", "girl"),
            ("Hoodie", "hoodie"),
            ("Mob", "mob"),
            ("YouTuber", "creator"),
            ("Dark", "dark"),
            ("Cute", "cute")
        ]

        self.tag_buttons = {}
        for label, tag_val in popular_tags:
            btn_tag = QPushButton(label)
            btn_tag.setObjectName("TagButtonActive" if tag_val == "" else "TagButton")
            btn_tag.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_tag.clicked.connect(lambda checked, t=tag_val: self.on_tag_selected(t))
            tags_layout.addWidget(btn_tag)
            self.tag_buttons[tag_val] = btn_tag

        tags_layout.addStretch()
        tags_scroll.setWidget(tags_container)
        right_layout.addWidget(tags_scroll)

        # Sezione Ricerca per Nome o Tag
        search_box = QHBoxLayout()
        search_box.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca skin per nome o tag (es. dream, gojo, boy, hoodie)...")
        self.search_input.setObjectName("SearchInput")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_box.addWidget(self.search_input, 1)

        self.total_count_label = QLabel("0 skin")
        self.total_count_label.setStyleSheet("color: #38bdf8; font-size: 9pt; font-weight: bold; background: #1e293b; padding: 4px 8px; border-radius: 6px;")
        search_box.addWidget(self.total_count_label)

        right_layout.addLayout(search_box)

        # Area scrollabile griglia skin
        lib_scroll = QScrollArea()
        lib_scroll.setWidgetResizable(True)
        lib_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lib_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lib_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.lib_container = QWidget()
        self.grid_layout = QGridLayout(self.lib_container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        lib_scroll.setWidget(self.lib_container)
        right_layout.addWidget(lib_scroll, 1)

        # Paginazione
        pagination_layout = QHBoxLayout()
        pagination_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.setSpacing(12)

        self.btn_prev = QPushButton("< Precedente")
        self.btn_prev.setObjectName("SecondaryButton")
        self.btn_prev.clicked.connect(self.prev_page)

        self.page_label = QLabel("Pagina 1")
        self.page_label.setStyleSheet("color: #94a3b8; font-weight: 500;")

        self.btn_next = QPushButton("Successiva >")
        self.btn_next.setObjectName("SecondaryButton")
        self.btn_next.clicked.connect(self.next_page)

        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_next)
        right_layout.addLayout(pagination_layout)

        # Pulsante principale: Applica
        self.apply_btn = QPushButton("Applica Skin all'Account Microsoft")
        self.apply_btn.setObjectName("ApplySkinButton")
        self.apply_btn.setFixedHeight(44)
        self.apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_btn.clicked.connect(self.apply_skin_to_account)
        right_layout.addWidget(self.apply_btn)

        splitter.addWidget(right_panel, 1)
        main_layout.addLayout(splitter, 1)

        # Bottom row
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton("Chiudi")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)
        main_layout.addLayout(bottom_layout)

    # --- CATEGORIE E FILTRI ---
    def on_category_changed(self, category_text):
        if category_text == "Tutte le Categorie":
            self.active_category = "Tutte"
        else:
            self.active_category = category_text
        self.pages_cache.clear()
        self.load_catalog_page(1)

    def on_sort_changed(self, idx):
        self.active_sort = self.sort_combo.currentData() or "popolari"
        self.pages_cache.clear()
        self.load_catalog_page(1)

    def on_tag_selected(self, tag_val):
        self.active_tag = tag_val
        for t, btn in self.tag_buttons.items():
            if t == tag_val:
                btn.setObjectName("TagButtonActive")
            else:
                btn.setObjectName("TagButton")
            # Forza ricalcolo stile Qt6: unpolish + polish ri-legge l'objectName
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        self.pages_cache.clear()
        self.load_catalog_page(1)

    def on_search_text_changed(self, text):
        self.search_query = text.strip()
        self.pages_cache.clear()
        self.load_catalog_page(1)

    def search_player_skin(self):
        self.on_search_text_changed(self.search_input.text())

    def load_catalog_page(self, page_num):
        self.current_page = max(1, page_num)

        # Interrompiamo eventuali thread attivi precedenti
        for t in self.active_threads:
            if t.isRunning():
                t.quit()
                t.wait(100)
        self.active_threads.clear()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.card_labels.clear()

        cache_key = (self.search_query, self.active_category, self.active_sort, self.active_tag, self.current_page)
        if cache_key in self.pages_cache:
            items, total_count = self.pages_cache[cache_key]
            self.render_items(items, total_count)
            return

        # Mostra indicatore di caricamento e disabilita navigazione
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        loading_lbl = QLabel("Caricamento skin in corso...")
        loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_lbl.setStyleSheet("color: #64748b; font-size: 10pt; padding: 24px;")
        self.grid_layout.addWidget(loading_lbl, 0, 0, 1, 3)

        thread = QThread(self)
        worker = MineskinCatalogWorker(
            page=self.current_page,
            size=self.page_size,
            search_query=self.search_query,
            category=self.active_category,
            sort_by=self.active_sort,
            tag=self.active_tag
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        def on_loaded(items, total_count):
            # Scarta risultati se i filtri sono cambiati nel frattempo
            if (worker.search_query != self.search_query.strip().lower()
                    or worker.tag != self.active_tag
                    or worker.category != self.active_category
                    or worker.sort_by != self.active_sort):
                return
            self.pages_cache[cache_key] = (items, total_count)
            self.render_items(items, total_count)

        worker.finished.connect(on_loaded)
        worker.finished.connect(thread.quit)
        worker.error.connect(lambda err: show_warning(self, "Errore Catalogo", err))
        worker.error.connect(thread.quit)

        self.catalog_worker = worker
        self.active_threads.append(thread)
        thread.start()

    def render_items(self, items, total_count):
        self.filtered_skins = items
        self.total_items_count = total_count

        # Pulisce il grid (incluso eventuale loading label)
        while self.grid_layout.count():
            it = self.grid_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Pagina {self.current_page} / {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        self.total_count_label.setText(f"{total_count} skin")

        if not items:
            empty_lbl = QLabel("Nessuna skin trovata.\nProva a cambiare i filtri o cerca un nome diverso.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setWordWrap(True)
            empty_lbl.setStyleSheet("color: #64748b; font-size: 10pt; padding: 24px;")
            self.grid_layout.addWidget(empty_lbl, 0, 0, 1, 3)
            return

        for i, item in enumerate(items):
            card, img_label = self.create_skin_card(item)
            item_id = f"skin_{self.current_page}_{i}_{item.get('player') or item.get('name')}"
            self.card_labels[item_id] = img_label

            row = i // 3
            col = i % 3
            self.grid_layout.addWidget(card, row, col)

            self.load_card_thumbnail_async(item_id, item)

    def load_mineskin_catalog_page(self, page_num):
        self.load_catalog_page(page_num)

    def render_catalog_page(self, page_num):
        self.load_catalog_page(page_num)

    def create_skin_card(self, skin_info):
        name = skin_info.get("name", "Skin")
        is_popular = skin_info.get("popular", False)
        downloads = skin_info.get("downloads", 0)
        tags = skin_info.get("tags", [])
        variant = skin_info.get("variant", "classic")
        category = skin_info.get("category", "")

        # Formato download compatto
        if downloads >= 1000:
            dl_str = f"{downloads // 1000}k"
        else:
            dl_str = str(downloads) if downloads else ""

        btn = QPushButton()
        btn.setObjectName("SkinCardButton")
        btn.setFixedSize(110, 130)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Tooltip ricco con tutte le informazioni
        tag_str = ", ".join(tags[:6]) if tags else "-"
        tooltip = f"<b>{name}</b><br>Modello: {variant.title()}"
        if category:
            tooltip += f"<br>Categoria: {category}"
        if dl_str:
            tooltip += f"<br>Download: ~{dl_str}"
        if tag_str:
            tooltip += f"<br>Tag: {tag_str}"
        btn.setToolTip(tooltip)

        layout = QVBoxLayout(btn)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        img_label = QLabel()
        img_label.setFixedSize(54, 84)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background: transparent; border-radius: 6px; color: #64748b; font-size: 8pt;")
        img_label.setText("Carica...")
        layout.addWidget(img_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Nome skin troncato senza emoji
        name_short = name if len(name) <= 12 else name[:11] + "…"
        name_lbl = QLabel(name_short)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("color: #f1f5f9; font-size: 7.5pt; font-weight: 600; background: transparent;")
        layout.addWidget(name_lbl)

        # Download count (piccolo, grigio, senza emoji)
        if dl_str:
            dl_lbl = QLabel(f"{dl_str} dl")
            dl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dl_lbl.setStyleSheet("color: #475569; font-size: 7pt; background: transparent;")
            layout.addWidget(dl_lbl)

        btn.clicked.connect(lambda: self.select_catalog_skin(skin_info))
        return btn, img_label

    def load_card_thumbnail_async(self, item_id, item_data):
        thread = QThread(self)
        worker = ThumbnailWorker(item_id, item_data)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.thumbnail_ready.connect(self.on_thumbnail_ready)
        worker.thumbnail_ready.connect(thread.quit)

        self.card_threads.append(thread)
        self.card_workers.append(worker)
        thread.start()

    def on_thumbnail_ready(self, item_id, pixmap):
        if item_id in self.card_labels:
            scaled = pixmap.scaled(54, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.card_labels[item_id].setPixmap(scaled)

    def prev_page(self):
        if self.current_page > 1:
            self.load_catalog_page(self.current_page - 1)

    def next_page(self):
        total_pages = max(1, (self.total_items_count + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.load_catalog_page(self.current_page + 1)

    def select_catalog_skin(self, skin_info):
        name = skin_info.get("name", "Skin")
        variant = skin_info.get("variant", "classic")
        self.skin_name_badge.setText(f"Caricamento: {name}...")

        if self.skin_download_thread and self.skin_download_thread.isRunning():
            self.skin_download_thread.quit()
            self.skin_download_thread.wait(100)

        thread = QThread(self)
        worker = SkinDownloadWorker(skin_info)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        def on_ready(skin_bytes, chosen_variant, display_name):
            self.current_skin_bytes = skin_bytes
            self.current_model = chosen_variant
            self.skin_name_badge.setText(name)
            self.radio_classic.blockSignals(True)
            self.radio_slim.blockSignals(True)
            if chosen_variant == "slim":
                self.radio_slim.setChecked(True)
                self.radio_classic.setChecked(False)
            else:
                self.radio_classic.setChecked(True)
                self.radio_slim.setChecked(False)
            self.radio_classic.blockSignals(False)
            self.radio_slim.blockSignals(False)
            self.update_3d_preview()
            self.skin_download_worker = None  # Rilascia dopo completamento

        def on_error(err):
            self.skin_name_badge.setText(name)
            show_warning(self, "Errore Download", err)
            self.skin_download_worker = None  # Rilascia anche in caso di errore

        worker.finished.connect(on_ready)
        worker.finished.connect(thread.quit)
        worker.error.connect(on_error)
        worker.error.connect(thread.quit)

        self.skin_download_thread = thread
        self.skin_download_worker = worker  # IMPORTANTE: mantieni worker vivo per prevenire GC prematura
        self.active_threads.append(thread)
        thread.start()

    # --- CARICAMENTO SKIN LOCALE E ACCOUNT ---
    def load_account_current_skin(self):
        username = self.account.get('username')
        user_uuid = self.account.get('uuid')
        
        # Prova prima dai server ufficiali Mojang
        try:
            skin_bytes, variant, _, _ = resolve_mojang_skin(user_uuid or username)
            self.current_skin_bytes = skin_bytes
            self.current_model = variant
            if variant == "slim":
                self.radio_slim.setChecked(True)
            else:
                self.radio_classic.setChecked(True)
            self.skin_name_badge.setText(f"In uso: {username}")
            self.update_3d_preview()
            return
        except Exception:
            pass

        # Fallback su Crafatar
        try:
            url = f"https://crafatar.com/skins/{username}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and len(res.content) > 100:
                self.current_skin_bytes = res.content
                self.skin_name_badge.setText(f"In uso: {username}")
                self.update_3d_preview()
                return
        except Exception:
            pass

        # Fallback finale: Steve
        self.select_catalog_skin({"name": "Steve Classic", "player": "Steve", "variant": "classic"})

    def browse_local_skin(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona file skin PNG", "", "Immagini PNG (*.png);;Tutti i file (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                if len(content) > 100:
                    self.current_skin_bytes = content
                    base_name = os.path.basename(file_path)
                    self.skin_name_badge.setText(f"File: {base_name}")
                    self.update_3d_preview()
                else:
                    show_warning(self, "File non valido", "Il file selezionato è troppo piccolo o vuoto.")
            except Exception as e:
                show_warning(self, "Errore", f"Impossibile leggere il file: {e}")

    def export_current_skin_png(self):
        if not self.current_skin_bytes:
            show_warning(self, "Attenzione", "Nessuna skin attualmente caricata da salvare.")
            return

        suggested_name = f"skin_{self.current_model}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salva Skin PNG", suggested_name, "Immagini PNG (*.png)"
        )
        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(self.current_skin_bytes)
                CustomMessageBox.information(self, "Salvataggio completato", f"Skin salvata con successo in:\n{file_path}")
            except Exception as e:
                show_warning(self, "Errore salvataggio", f"Impossibile salvare il file: {e}")

    # --- ANTEPRIMA 3D & EVENTI MODELLO ---
    def on_model_changed(self):
        if self.radio_slim.isChecked():
            self.current_model = "slim"
        else:
            self.current_model = "classic"
        
        if self.current_skin_bytes:
            self.update_3d_preview()

    def on_anim_changed(self, idx):
        anims = ["walk", "run", "idle"]
        self.current_anim = anims[idx] if 0 <= idx < len(anims) else "walk"
        if self.current_skin_bytes:
            self.update_3d_preview()

    def update_3d_preview(self):
        if not self.current_skin_bytes:
            return

        b64 = base64.b64encode(self.current_skin_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64}"

        # skinview3d usa "default" (non "classic") e "slim"
        sv3d_model = "slim" if self.current_model == "slim" else "default"

        # Se la pagina 3D è già stata caricata e il viewer esiste, aggiorniamo al volo con JS per reattività immediata
        if getattr(self, "skin_viewer_ready", False):
            js_update = f"""
            (function() {{
                try {{
                    if (window.skinViewer) {{
                        window.skinViewer.loadSkin("{data_uri}", {{ model: "{sv3d_model}" }});
                        if (window.updateAnimation) {{
                            window.updateAnimation("{self.current_anim}");
                        }}
                    }}
                }} catch(e) {{
                    console.error("loadSkin error:", e);
                }}
            }})();
            """
            self.web_view.page().runJavaScript(js_update)
            return

        # Configurazione animazione iniziale skinview3d
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    margin: 0;
                    background-color: #101216;
                    color: #fff;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    overflow: hidden;
                    font-family: 'Segoe UI', Tahoma, sans-serif;
                }}
                #skin_container {{
                    width: 100%;
                    height: 100%;
                }}
                .loading {{
                    position: absolute;
                    color: #94a3b8;
                    font-size: 14px;
                    pointer-events: none;
                }}
            </style>
            <script>
                {self.skinview3d_js}
            </script>
        </head>
        <body>
            <div id="skin_container"></div>
            <div id="loading" class="loading">Caricamento 3D...</div>
            <script>
                try {{
                    let container = document.getElementById('skin_container');
                    container.style.width = '100%';
                    container.style.height = '100%';

                    let canvas = document.createElement('canvas');
                    canvas.style.display = 'block';
                    canvas.style.width = '100%';
                    canvas.style.height = '100%';
                    container.appendChild(canvas);

                    let w = container.clientWidth || 320;
                    let h = container.clientHeight || 460;

                    window.skinViewer = new skinview3d.SkinViewer({{
                        canvas: canvas,
                        width: w,
                        height: h,
                        skin: "{data_uri}",
                        model: "{sv3d_model}"
                    }});
                    window.skinViewer.fov = 50;
                    window.skinViewer.zoom = 0.85;

                    window.updateAnimation = function(animName) {{
                        if (!window.skinViewer) return;
                        if (animName === "walk") {{
                            window.skinViewer.animation = new skinview3d.WalkingAnimation();
                            window.skinViewer.animation.speed = 0.6;
                        }} else if (animName === "run") {{
                            window.skinViewer.animation = new skinview3d.RunningAnimation();
                            window.skinViewer.animation.speed = 0.8;
                        }} else {{
                            window.skinViewer.animation = null;
                        }}
                    }};

                    window.updateAnimation("{self.current_anim}");

                    document.getElementById('loading').style.display = 'none';

                    window.addEventListener('resize', () => {{
                        if (window.skinViewer) {{
                            let nw = container.clientWidth || 320;
                            let nh = container.clientHeight || 460;
                            window.skinViewer.width = nw;
                            window.skinViewer.height = nh;
                        }}
                    }});
                }} catch(e) {{
                    document.getElementById('loading').innerText = "Render 3D non disponibile: " + e.message;
                }}
            </script>
        </body>
        </html>
        """
        self.skin_viewer_ready = True
        self.web_view.setHtml(html, QUrl("http://localhost/"))

    # --- APPLICAZIONE ALL'ACCOUNT MICROSOFT ---
    def ensure_valid_access_token(self):
        """Verifica se il token è valido; se scaduto, tenta il rinnovo con refresh_token."""
        access_token = self.account.get("access_token")
        refresh_token = self.account.get("refresh_token")

        # Verifica scadenza
        is_expired = False
        if self.account_manager and hasattr(self.account_manager, "is_token_expired"):
            is_expired = self.account_manager.is_token_expired()

        if (not access_token or is_expired) and refresh_token and self.client_id:
            try:
                import minecraft_launcher_lib
                new_data = minecraft_launcher_lib.microsoft_account.complete_refresh(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri="http://localhost:5000/callback",
                    refresh_token=refresh_token
                )
                if self.account_manager:
                    self.account = self.account_manager.add_microsoft_account(new_data)
                else:
                    self.account.update(new_data)
                return self.account.get("access_token")
            except Exception as e:
                print(f"[SkinManager] Errore rinnovo automatico token: {e}")

        return access_token

    def apply_skin_to_account(self):
        if not self.current_skin_bytes:
            show_warning(self, "Attenzione", "Nessuna skin selezionata da applicare.")
            return

        if self.account.get("type") != "microsoft":
            show_warning(self, "Account Offline", "Impossibile applicare la skin direttamente sui server Microsoft con un account offline. Effettua l'accesso con un profilo Microsoft valido.")
            return

        access_token = self.ensure_valid_access_token()
        if not access_token:
            show_warning(self, "Errore di Autenticazione", "Token di accesso Microsoft mancante o scaduto. Effettua nuovamente l'accesso con il profilo Microsoft.")
            return

        try:
            self.apply_btn.setEnabled(False)
            self.apply_btn.setText("Applicazione skin sui server Mojang...")
            QApplication.processEvents()

            url = "https://api.minecraftservices.com/minecraft/profile/skins"
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            files = {
                "file": ("skin.png", self.current_skin_bytes, "image/png")
            }
            variant_val = "SLIM" if self.current_model == "slim" else "CLASSIC"
            data = {
                "variant": variant_val
            }

            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
            
            if response.status_code in [200, 204]:
                # Invalida la cache locale della testa/avatar per forzare il ricaricamento
                self.invalidate_local_head_cache()

                CustomMessageBox.information(
                    self, "Successo", "La nuova skin e' stata applicata con successo al tuo account Microsoft!"
                )
                self.accept()
            elif response.status_code == 401:
                show_warning(self, "Token Scaduto", "La sessione Microsoft è scaduta. Riapri la gestione account ed effettua nuovamente il login.")
            else:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("errorMessage") or err_json.get("message") or response.text
                except Exception:
                    err_msg = response.text
                show_warning(self, "Errore API Minecraft", f"Impossibile applicare la skin ({response.status_code}):\n{err_msg}")
        except Exception as e:
            show_warning(self, "Errore", f"Errore durante l'applicazione della skin: {e}")
        finally:
            self.apply_btn.setEnabled(True)
            self.apply_btn.setText("Applica Skin all'Account Microsoft")

    def invalidate_local_head_cache(self):
        """Elimina la cache dell'avatar dell'account per forzare il refresh immediato nel launcher."""
        try:
            heads_folder = os.path.expanduser("~/.cignolauncher/heads")
            username = self.account.get("username")
            uuid_val = self.account.get("uuid")
            for key in [username, uuid_val]:
                if key:
                    path = os.path.join(heads_folder, f"{key}.png")
                    if os.path.exists(path):
                        os.remove(path)
        except Exception as e:
            print(f"[SkinManager] Errore invalidazione cache head: {e}")

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f1115;
                color: #f8fafc;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            }
            QFrame#PreviewCard, QFrame#SidebarCard {
                background-color: #161922;
                border: 1px solid #2a2e3d;
                border-radius: 12px;
            }
            QLineEdit#SearchInput {
                background-color: #1e222d;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f8fafc;
                padding: 7px 12px;
                font-size: 9.5pt;
            }
            QLineEdit#SearchInput:focus {
                border-color: #3b82f6;
            }
            QComboBox {
                background-color: #1e222d;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f8fafc;
                padding: 5px 10px;
                font-size: 9.5pt;
            }
            QComboBox QAbstractItemView {
                background-color: #1e222d;
                color: #f8fafc;
                selection-background-color: #2563eb;
                border: 1px solid #334155;
            }
            QPushButton#SecondaryButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 500;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #334155;
            }
            QPushButton#SecondaryButtonSmall {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 8.5pt;
            }
            QPushButton#SecondaryButtonSmall:hover {
                background-color: #334155;
            }
            QPushButton#PrimaryActionButtonSmall {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton#PrimaryActionButtonSmall:hover {
                background-color: #1d4ed8;
            }
            QPushButton#SkinCardButton {
                background-color: #1a1e28;
                border: 1px solid #2a2e3d;
                border-radius: 10px;
            }
            QPushButton#SkinCardButton:hover {
                background-color: #242a38;
                border-color: #3b82f6;
            }
            QPushButton#ApplySkinButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton#ApplySkinButton:hover {
                background-color: #059669;
            }
            QRadioButton {
                color: #f8fafc;
                spacing: 8px;
                font-size: 9.5pt;
            }
            QPushButton#TagButton {
                background-color: #1e222d;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 13px;
                padding: 3px 10px;
                font-size: 8.5pt;
                font-weight: 500;
            }
            QPushButton#TagButton:hover {
                background-color: #2a3142;
                color: #f8fafc;
                border-color: #38bdf8;
            }
            QPushButton#TagButtonActive {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 13px;
                padding: 3px 10px;
                font-size: 8.5pt;
                font-weight: bold;
            }
        """)

