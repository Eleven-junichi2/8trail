from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import sys

from .gametext import TextSurfaceFactory

import pygame


def open_json_file(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


@dataclass
class Arrow:
    """Arrow symbol"""
    up = 0
    down = 1
    right = 2
    left = 3


@dataclass
class ArrowToTurnToward:
    """Use to set direction"""
    is_up: bool = field(default=False)
    is_down: bool = field(default=False)
    is_right: bool = field(default=False)
    is_left: bool = field(default=False)

    def set(self, direction: Arrow):
        if direction is Arrow.up:
            self.is_up = True
        elif direction is Arrow.down:
            self.is_down = True
        elif direction is Arrow.right:
            self.is_right = True
        elif direction is Arrow.left:
            self.is_left = True

    def unset(self, direction: Arrow):
        if direction is Arrow.up:
            self.is_up = False
        elif direction is Arrow.down:
            self.is_down = False
        elif direction is Arrow.right:
            self.is_right = False
        elif direction is Arrow.left:
            self.is_left = False

    # def switch(self, direction: Arrow):
    #     if direction is Arrow.up:
    #         self.is_down = False
    #     elif direction is Arrow.down:
    #         self.is_down = not self.is_down
    #     elif direction is Arrow.right:
    #         self.is_right = self.is_right
    #     elif direction is Arrow.left:
    #         self.is_left = self.is_left

    def is_set_any(self):
        return True in set(asdict(self).values())


class AssetFilePath:
    root_dirname = "assets"
    root = Path(sys.argv[0]).parent / root_dirname
    img_dirname = "imgs"
    font_dirname = "fonts"
    sound_dirname = "sounds"
    level_dirname = "level_data"

    @ classmethod
    def pyinstaller_path(cls, filepath):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            path = Path(sys._MEIPASS) / cls.root_dirname / filepath
            # path will be such as: "sys._MEIPASS/assets/imgs/example.png"
        except AttributeError:
            path = cls.root / filepath
        return path

    @ classmethod
    def img(cls, filename):
        return cls.pyinstaller_path(Path(cls.img_dirname) / filename)

    @ classmethod
    def font(cls, filename):
        return cls.pyinstaller_path(Path(cls.font_dirname) / filename)

    @ classmethod
    def sound(cls, filename):
        return cls.pyinstaller_path(Path(cls.sound_dirname) / filename)

    @ classmethod
    def level(cls, filename):
        return cls.pyinstaller_path(Path(cls.level_dirname) / filename)


class TextToDebug:
    """
    Example:
        clock = pygame.time.Clock()
        surface_object = pygame.surface.Surface((10, 10))
        TextToDebug.fps(clock) # prepare text before do render()
        TextToDebug.render("fps", surface_object, (10, 20))
    """
    _debug_text_factory = TextSurfaceFactory()
    _debug_text_factory.register_font(
        "misaki",
        pygame.font.Font(AssetFilePath.font("misaki_gothic.ttf"), 16))
    render = _debug_text_factory.render

    @classmethod
    def arrow_keys(cls, key):
        key_text = f"↑{key[pygame.K_UP]}"
        key_text += f"↓{key[pygame.K_DOWN]}"
        key_text += f"←{key[pygame.K_LEFT]}"
        key_text += f"→{key[pygame.K_RIGHT]}"
        cls._debug_text_factory.register_text("arrow_keys", key_text)

    @classmethod
    def arrow_keys_from_event(cls, event_key):
        key_text = f"↑{event_key == pygame.K_UP}"
        key_text += f"↓{event_key == pygame.K_DOWN}"
        key_text += f"←{event_key == pygame.K_LEFT}"
        key_text += f"→{event_key == pygame.K_RIGHT}"
        cls._debug_text_factory.register_text(
            "arrow_keys_from_event", key_text)

    @classmethod
    def fps(cls, clock: pygame.time.Clock):
        cls._debug_text_factory.register_text("fps", f"FPS:{clock.get_fps()}")
