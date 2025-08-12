from collections import UserDict
import copy
from inspect import isclass
import math


# from typing import Any
# from .keyboard import Keyboard
from .entity import DeadlyObstacle, Entity, EntityList, ShooterEntity, Enemy
from .gameinput import Joystick2
from .gamelevel import Level
from .gamescene import Scene, SceneManager
from .gametext import TextSurfaceFactory
from .ui import UIBoxLayout, UIElement, UIGameText
from .utilities import Arrow, ArrowToTurnToward, AssetFilePath, TextToDebug  # noqa
from .schedule import IntervalCounter, schedule_instance_method_interval
from .sound import SoundDict, ChannelManager

import pygame

from .animation import AnimationDict, AnimationImage, AnimationFactory, SpriteSheet

from . import global_
from .global_ import init  # noqa

# TODO: Fix game reset bug
# TODO: Replace movement direction process to use angle

pygame.init()
pygame.mixer.init()
pygame.joystick.init()

try:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick Name: " + joystick.get_name())
    print("Number of Button : " + str(joystick.get_numbuttons()))
    print("Number of Axis : " + str(joystick.get_numaxes()))
    print("Number of Hats : " + str(joystick.get_numhats()))
except Exception as e:
    print(e)
    joystick = None

clock = pygame.time.Clock()
fps = 60

textfactory = TextSurfaceFactory()
textfactory.register_font(
    "misaki_gothic", pygame.font.Font(AssetFilePath.font("misaki_gothic.ttf"), 16)
)

SE_VOLUME_DEFAULT = 0.8
channel_manager = ChannelManager()
channel_manager.register("enemy", pygame.mixer.Channel(0), SE_VOLUME_DEFAULT)
channel_manager.register("player", pygame.mixer.Channel(1), SE_VOLUME_DEFAULT)
sound_dict = SoundDict()
sound_dict["explosion"] = pygame.mixer.Sound(AssetFilePath.sound("explosion1.wav"))
sound_dict["enemy_death1"] = pygame.mixer.Sound(AssetFilePath.sound("deathse2.wav"))
sound_dict["enemy_death2"] = pygame.mixer.Sound(AssetFilePath.sound("deathse3.wav"))
sound_dict["player_death"] = pygame.mixer.Sound(AssetFilePath.sound("explosion2.wav"))
sound_dict["shot"] = pygame.mixer.Sound(AssetFilePath.sound("shot1.wav"))
sound_dict["laser"] = pygame.mixer.Sound(AssetFilePath.sound("laser2.wav"))
music_dict = {
    "gameover": AssetFilePath.sound("music/gameover.wav"),
    "space_battle": AssetFilePath.sound("music/bgm1.wav"),
}

show_hitbox = False


class Explosion(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("explosion_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 16, 16),
            self.sprite_sheet.image_by_area(0, 16, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 2, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 3, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 4, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 5, 16, 16),
        ]
        self.anim_interval = 3


class PlayerExplosion(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("explosion_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 22, 22),
            self.sprite_sheet.image_by_area(0, 22, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 2, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 3, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 4, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 5, 22, 22),
        ]
        self.anim_interval = 2


class FighterIdle(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 22 * 2, 22, 22),
        ]


class FighterRollLeft(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 22, 22),
            self.sprite_sheet.image_by_area(0, 22, 22, 22),
        ]
        self.anim_interval = 15
        self.is_loop = False


class FighterRollRight(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 22 * 3, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 4, 22, 22),
        ]
        self.anim_interval = 15
        self.is_loop = False


class ScoutDiskIdle(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 16, 16),
            self.sprite_sheet.image_by_area(0, 16, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 2, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 3, 16, 16),
        ]
        self.anim_interval = 5


class ScoutDiskMove(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 16 * 4, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 5, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 6, 16, 16),
            self.sprite_sheet.image_by_area(0, 16 * 7, 16, 16),
        ]
        self.anim_interval = 5


class ScoutDisk2Idle(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("scoutdisk.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 18, 18),
        ]
        self.anim_interval = 5


class ScoutDisk2Move(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("scoutdisk.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 18 * 1, 18, 18),
            self.sprite_sheet.image_by_area(0, 18 * 2, 18, 18),
        ]
        self.anim_interval = 5


class TrumplaIdle(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 16, 16),
        ]
        self.anim_interval = 5


class TrumplaRollLeft(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 16 * 3, 16, 16),
        ]
        self.anim_interval = 10


class TrumplaRollRight(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 16, 16, 16),
        ]
        self.anim_interval = 10


class TrumplaAttack(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 16 * 4, 16, 16),
            self.sprite_sheet.image_by_area(0, 0, 16, 16),
        ]
        self.anim_interval = 20


class EnemyShotAnim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("enemy_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 4, 4),
            self.sprite_sheet.image_by_area(0, 4, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 2, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 3, 4, 4),
        ]
        self.anim_interval = 6


class EnemyShot2Anim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("shot3.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 4, 4),
            self.sprite_sheet.image_by_area(0, 4, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 2, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 3, 4, 4),
        ]
        self.anim_interval = 6


class EnemyShot3Anim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("shot5.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 4, 4),
            self.sprite_sheet.image_by_area(0, 4, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 2, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 3, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 4, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 5, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 6, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 7, 4, 4),
        ]
        self.anim_interval = 6


class EnemyShot4Anim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("shot6.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 6, 6),
            self.sprite_sheet.image_by_area(0, 6, 6, 6),
            self.sprite_sheet.image_by_area(0, 6 * 2, 6, 6),
            self.sprite_sheet.image_by_area(0, 6 * 3, 6, 6),
        ]
        self.anim_interval = 6


class EnemyShot5Anim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("shot7.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 4, 4),
            self.sprite_sheet.image_by_area(0, 4, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 2, 4, 4),
            self.sprite_sheet.image_by_area(0, 4 * 3, 4, 4),
        ]
        self.anim_interval = 6


class EnemyShot6Anim(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("shot8.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 5, 5),
            self.sprite_sheet.image_by_area(0, 5, 5, 5),
            self.sprite_sheet.image_by_area(0, 5 * 2, 5, 5),
            self.sprite_sheet.image_by_area(0, 5 * 3, 5, 5),
        ]
        self.anim_interval = 4


class PlayerShot(Entity):
    def __init__(
        self, shooter_sprite: ShooterEntity, shot_que: EntityList, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.shot_que = shot_que
        self.image = pygame.image.load(AssetFilePath.img("shot1.png"))
        self.shooter = shooter_sprite
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.reset_pos_x()
        self.reset_pos_y()
        self.movement_speed = 5
        self.is_launching = False

    def reset_pos_x(self):
        self.x = self.shooter.x + self.shooter.rect.width / 2 - self.rect.width / 2

    def reset_pos_y(self):
        self.y = self.shooter.y + self.shooter.rect.height / 2 - self.rect.height

    def will_launch(self, direction: Arrow):
        self.arrow_of_move.set(direction)
        self.entity_container.append(self)
        self.is_launching = True

    def _fire(self, dt):
        if self.is_launching:
            self.move_on(dt)
            if (
                self.y < 0
                or global_.w_size[1] < self.y
                or self.x < 0
                or global_.w_size[0] < self.x
            ):
                self.arrow_of_move.unset(Arrow.up)
                self.is_launching = False
                self.reset_pos_x()
                self.reset_pos_y()
                self.allow_shooter_to_fire()
                self.death()

    def move_on(self, dt):
        self.move_by_arrow(dt)

    def death(self):
        """Remove sprite from group and que of shooter."""
        if self in self.shot_que:
            self.shot_que.remove(self)
            self.remove_from_container()
            self.is_launching = False

    def allow_shooter_to_fire(self):
        self.shooter.is_shot_allowed = True

    def update(self, dt):
        if not self.is_launching:
            self.reset_pos_x()
            self.reset_pos_y()
        self._fire(dt)


class PlayerLaser(PlayerShot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.image.load(AssetFilePath.img("laser1.png"))
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.movement_speed = 6
        self.reset_pos_x()
        self.reset_pos_y()

    def move_by_arrow(self, dt):
        self.reset_pos_x()
        super().move_by_arrow(dt)


class PlayerMissile(PlayerShot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.image.load(AssetFilePath.img("shot2.png"))
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.movement_speed = 2.75
        self.reset_pos_x()
        self.reset_pos_y()
        self.angle_to_target = math.radians(-90)

    def move_on(self, dt):
        # self.homing_another_target(dt)
        self.homing_single_target(dt)

    def allow_shooter_to_fire(self):
        self.shooter.is_missile_allowed = True

    def homing_another_target(self, dt):
        # TODO: Fix movement speed
        missiles = self.gameworld.entities_by_type(type(self))
        if self.gameworld.enemies():
            distance_list = []
            for enemy in self.gameworld.enemies():
                distance = math.sqrt(
                    (enemy.hitbox.centerx - self.hitbox.centerx) ** 2
                    + (enemy.hitbox.centery - self.hitbox.centery) ** 2
                )
                distance_list.append(distance)
            sorted_distance_list = copy.deepcopy(distance_list)
            sorted_distance_list.sort()
            sorted_distance_list = sorted_distance_list[: len(missiles)]
            for i, distance in enumerate(sorted_distance_list):
                target_enemy_index = distance_list.index(distance)
                target = self.gameworld.enemies()[target_enemy_index]
                # print(i, math.atan2(
                #     target.rect.centery - missiles[i].rect.centery,
                #     target.rect.centerx - missiles[i].rect.centerx))
                missiles[i].angle_to_target = math.atan2(
                    target.rect.centery - missiles[i].rect.centery,
                    target.rect.centerx - missiles[i].rect.centerx,
                )
                missiles[i].move_by_angle(dt, missiles[i].angle_to_target)
        else:
            self.angle_to_target = math.radians(-90)
            self.move_by_angle(dt, self.angle_to_target)

    def homing_single_target(self, dt):
        if len(self.gameworld.enemies()) > 0:
            distance_list = []
            for enemy in self.gameworld.enemies():
                distance = math.sqrt(
                    (enemy.hitbox.centerx - self.hitbox.centerx) ** 2
                    + (enemy.hitbox.centery - self.hitbox.centery) ** 2
                )
                distance_list.append(distance)
            target_enemy_index = distance_list.index(min(distance_list))
            target = self.gameworld.enemies()[target_enemy_index]
            self.angle_to_target = math.atan2(
                target.rect.centery - self.rect.centery,
                target.rect.centerx - self.rect.centerx,
            )
            # print(f"single atan2 {self.angle_to_target}")
            self.move_by_angle(dt, self.angle_to_target)
        else:
            self.angle_to_target = math.radians(-90)
            self.move_by_angle(dt, self.angle_to_target)


class ScoutDiskEnemy(Enemy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.death_sound = sound_dict["enemy_death1"]
        self.visual_effects = AnimationFactory()
        self.visual_effects["death"] = Explosion
        self.animation = AnimationDict()
        self.animation["idle"] = ScoutDisk2Idle()
        self.animation["move"] = ScoutDisk2Move()
        self.image = self.animation[self.action].image
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.hitbox.width = 10
        self.hitbox.height = 10
        self.movement_speed = 2
        self.behavior_pattern = None
        self.behavior_pattern_dict["strike_to_player"] = self.move_strike_to_player
        self.gamescore = 10
        # self.is_moving = True

    def update(self, dt):
        self.do_pattern(dt)
        if self.is_moving:
            self.action = "move"
        else:
            self.action = "idle"
        self.animation[self.action].let_continue_animation()
        self.image = self.animation[self.action].image
        self.animation[self.action].update(dt)

    def move_strike_to_player(self, dt):
        self.set_arrow_to_entity_as_dest(dt, Player)

    def death(self):
        visual_effect = self.visual_effects["death"]
        visual_effect.rect = self.rect
        visual_effect.let_play_animation()
        self.gameworld.scene.visual_effects.append(visual_effect)
        channel_manager["enemy"]["channel"].play(self.death_sound)
        super().death()


class TrumplaEnemy(ScoutDiskEnemy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.death_sound = sound_dict["enemy_death2"]
        self.animation = AnimationDict()
        self.animation["idle"] = TrumplaIdle()
        self.animation["roll_left"] = TrumplaRollLeft()
        self.animation["roll_right"] = TrumplaRollRight()
        self.animation["attack"] = TrumplaAttack()
        self.animation["attack"].loop_count = 1
        self.image = self.animation[self.action].image
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.hitbox.width = 10
        self.hitbox.height = 8
        self.movement_speed = 2.25
        self.gamescore = 10
        self.is_able_to_shot = True
        self.shot_interval = 45
        self.shot_range = 160

    def update(self, dt):
        # TODO: Fix shot animation
        # print(self.animation[self.action].was_played_once)
        self.do_pattern(dt)
        if self.is_moving:
            if self.arrow_of_move.is_left:
                self.action = "roll_left"
            elif self.arrow_of_move.is_right:
                self.action = "roll_right"
        else:
            self.action = "idle"
        player = self.gameworld.entity(Player)
        if player is not None:
            if self.is_entity_in_shot_range(player):
                self.action = "attack"
            else:
                self.animation["attack"]._loop_counter = 0
        # print("frame id", self.animation["attack"].anim_frame_id)
        # print("loop: ", self.animation["attack"]._loop_counter)
        # print("loop count", self.animation["attack"].loop_count)
        # print("loop is once finished", self.animation["attack"].is_finished)
        self.animation[self.action].let_continue_animation()
        self.animation[self.action].update(dt)

        self.launch_shot()

        self.image = self.animation[self.action].image

    def draw(self, screen):
        super().draw(screen)

    def draw_to_debug(self, screen):
        pygame.draw.circle(
            screen,
            (255, 0, 0),
            (self.hitbox.centerx, self.hitbox.centery),
            self.shot_range,
            1,
        )

    def is_entity_in_shot_range(self, entity: Entity) -> bool:
        distance = math.sqrt(
            (entity.hitbox.centerx - self.hitbox.centerx) ** 2
            + (entity.hitbox.centery - self.hitbox.centery) ** 2
        )
        return distance <= self.shot_range

    @schedule_instance_method_interval("shot_interval")
    def launch_shot(self):
        player = self.gameworld.entity(Player)
        if player is None:
            return
        if self.is_entity_in_shot_range(player):
            shot = EnemyShot(self)
            shot.x = self.rect.centerx - shot.rect.width // 2
            shot.y = self.rect.centery - shot.rect.height // 2
            shot.angle_to_target = math.atan2(
                player.rect.centery - self.rect.centery,
                player.rect.centerx - self.rect.centerx,
            )
            self.gameworld.entities.append(shot)
            shot.set_destination_to_entity(Player)
            self.animation[self.action].reset_animation()


class EnemyShot(DeadlyObstacle):
    def __init__(self, shooter_entity: Entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shooter = shooter_entity
        self.animation = AnimationDict()
        self.animation["idle"] = EnemyShot6Anim()
        self.animation["move"] = EnemyShot6Anim()
        self.action = "move"
        self.image = self.animation[self.action].image
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.hitbox.width = 4
        self.hitbox.height = 4
        self.invincible_to_entity = True
        self.movement_speed = 3
        self.behavior_pattern = "launching_aim_at_player"
        self.behavior_pattern_dict = {}
        self.behavior_pattern_dict["launching_aim_at_player"] = (
            self.move_launching_aim_at_player
        )
        self.gamescore = 10

    def update(self, dt):
        self.do_pattern(dt)

        # change image angle
        shot_angle = abs(math.degrees(self.angle_to_target))
        # print(shot_angle)
        if (60 < shot_angle < 120) or (240 < shot_angle < 300):
            self.animation[self.action].set_current_frame_id(0)
        elif (135 < shot_angle < 225) or ((315 < shot_angle) or (shot_angle < 45)):
            self.animation[self.action].set_current_frame_id(2)
        else:
            self.animation[self.action].let_continue_animation()
            self.animation[self.action].update(dt)
        self.animation[self.action].set_current_frame_to_image()
        self.image = self.animation[self.action].image

    def do_pattern(self, dt):
        if self.behavior_pattern is not None:
            self.behavior_pattern_dict[self.behavior_pattern](dt)

    def move_launching_aim_at_player(self, dt):
        self.move_by_angle(dt, self.angle_to_target)


class WeaponBulletFactory(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if isclass(value):
            self.data[key] = {}
            self.data[key]["entity"]: PlayerShot(value) = value
            self.data[key]["max_num"] = 1
            self.data[key]["interval"] = 1
        else:
            raise ValueError("The value must not be instance.")


class Player(ShooterEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shot_que = EntityList()
        self.weapon = WeaponBulletFactory()
        self.weapon["normal"] = PlayerShot
        self.weapon["normal"]["max_num"] = 4
        self.weapon["normal"]["interval"] = 3
        self.weapon["laser"] = PlayerLaser
        self.weapon["laser"]["max_num"] = 6
        self.weapon["laser"]["interval"] = 4
        self.change_weapon("normal")

        self.missile_que = EntityList()
        self.second_weapon = WeaponBulletFactory()
        self.second_weapon["normal"] = PlayerMissile
        self.second_weapon["normal"]["max_num"] = 2
        self.second_weapon["normal"]["interval"] = 3

        self.animation = AnimationDict()
        self.animation["idle"] = FighterIdle()
        self.animation["roll_left"] = FighterRollLeft()
        self.animation["roll_right"] = FighterRollRight()
        self.change_second_weapon("normal")

        self.visual_effects = AnimationFactory()
        self.visual_effects["explosion"] = PlayerExplosion

        self.death_sound = sound_dict["player_death"]
        self.normal_shot_sound = sound_dict["shot"]
        self.laser_shot_sound = sound_dict["laser"]

        self.action = "idle"
        self.image = self.animation[self.action].image
        self.rect = self.image.get_rect()
        self.hitbox = self.image.get_rect()
        self.hitbox.width = 8
        self.hitbox.height = self.rect.height * 0.8
        self.movement_speed = 3

        self.ignore_shot_interval = True
        self.is_shot_allowed = True

        self.ignore_missile_interval = True
        self.is_missile_allowed = True

    def change_weapon(self, weapon):
        self.current_weapon = weapon
        self.shot_interval = self.weapon[self.current_weapon]["interval"]

    def change_second_weapon(self, weapon):
        self.current_second_weapon = weapon
        self.missile_interval = self.second_weapon[self.current_second_weapon][
            "interval"
        ]

    @schedule_instance_method_interval(
        "shot_interval", interval_ignorerer="ignore_shot_interval"
    )
    def shooting(self):
        if self.is_shot_allowed and (
            len(self.shot_que) < self.weapon[self.current_weapon]["max_num"]
        ):
            if self.current_weapon == "normal":
                channel_manager["player"]["channel"].play(self.normal_shot_sound)
            elif self.current_weapon == "laser":
                if not pygame.mixer.get_busy():
                    channel_manager["player"]["channel"].play(self.laser_shot_sound)
            shot = self.weapon[self.current_weapon]["entity"](self, self.shot_que)
            shot.entity_container = self.entity_container
            shot.will_launch(Arrow.up)
            self.shot_que.append(shot)

    def on_release_trigger(self):
        if self.current_weapon == "laser":
            self.laser_shot_sound.stop()

    @schedule_instance_method_interval(
        "missile_interval", interval_ignorerer="ignore_missile_interval"
    )
    def shooting_missile(self):
        if self.is_missile_allowed and (
            len(self.missile_que)
            < self.second_weapon[self.current_second_weapon]["max_num"]
        ):
            if self.current_second_weapon == "normal":
                channel_manager["player"]["channel"].play(self.normal_shot_sound)
            missile = self.second_weapon[self.current_second_weapon]["entity"](
                self, self.missile_que
            )
            missile.entity_container = self.entity_container
            missile.will_launch(Arrow.up)
            self.missile_que.append(missile)

    def will_move_to(self, direction: Arrow):
        self.arrow_of_move.set(direction)
        if self.arrow_of_move.is_left:
            self.action = "roll_left"
        elif self.arrow_of_move.is_right:
            self.action = "roll_right"
        if not self.is_moving:
            self.animation[self.action].let_play_animation()
        self.is_moving = True

    def stop_moving_to(self, direction: Arrow):
        self.arrow_of_move.unset(direction)
        if not self.arrow_of_move.is_set_any():
            self.action = "idle"
            self.is_moving = False

    def update(self, dt):
        if self.current_weapon == "laser":
            if pygame.mixer.get_busy():
                if len(self.shot_que) == 0:
                    self.laser_shot_sound.stop()
        if self.is_moving:
            self.move_by_arrow(dt)

        if self.shot_que:
            self.ignore_shot_interval = False
        else:
            self.ignore_shot_interval = True

        if self.missile_que:
            self.ignore_missile_interval = False
        else:
            self.ignore_missile_interval = True

        self.do_animation(dt)

    def do_animation(self, dt):
        self.animation[self.action].update(dt)
        self.image = self.animation[self.action].image

    def death(self):
        if self in self.entity_container:
            explosion_effect = self.visual_effects["explosion"]
            explosion_effect.rect = self.rect
            explosion_effect.let_play_animation()
            self.gameworld.scene.visual_effects.append(explosion_effect)
            self.entity_container.kill_living_entity(self)
            channel_manager["player"]["channel"].play(self.death_sound)

    def draw(self, screen):
        super().draw(screen)

    def draw_to_debug(self, screen):
        centerpos = (self.rect.centerx, self.rect.centery)
        hitbox_centerpos = (self.hitbox.centerx, self.hitbox.centery)
        pygame.draw.line(screen, (0, 255, 0), centerpos, centerpos)
        pygame.draw.line(screen, (255, 122, 55), hitbox_centerpos, hitbox_centerpos)
        pygame.draw.line(screen, (155, 155, 155), (0, 0), hitbox_centerpos)


class GameScene(Scene):
    gamefont = pygame.font.Font(AssetFilePath.font("misaki_gothic.ttf"), 16)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gameworld = Level(AssetFilePath.level("stage1"), self)
        self.gameworld.set_background()
        self.gameworld.enemy_factory["scoutdisk"] = ScoutDiskEnemy
        self.gameworld.enemy_factory["trumpla"] = TrumplaEnemy
        self.init_player()
        self.init_text()
        self.gamelevel_running = True
        self.keyboard.register_keyaction(
            pygame.K_q, 0, 10, lambda: self.manager.transition_to(0)
        )

    def init_text(self):
        textfactory.register_text(
            "tutorial", "z:主砲 x:ミサイル c:主砲切り替え v:やり直す"
        )
        textfactory.register_text("gamescore", pos=[0, 32], color_rgb=[255, 255, 255])
        textfactory.register_text("highscore")
        textfactory.register_text("num_of_enemy", color_rgb=[255, 200, 200])
        textfactory.register_text("elapsed_time_in_level")
        textfactory.register_text("count_of_enemies_summoned")

    def init_player(self):
        self.player = Player()
        self.player.set_x_to_center_of_screen()
        self.player.y = global_.w_size[1] - self.player.rect.height
        self.gameworld.entities.append(self.player)
        self.keyboard.register_keyaction(
            pygame.K_UP,
            0,
            0,
            lambda: self.player.will_move_to(Arrow.up),
            lambda: self.player.stop_moving_to(Arrow.up),
        )
        self.keyboard.register_keyaction(
            pygame.K_DOWN,
            0,
            0,
            lambda: self.player.will_move_to(Arrow.down),
            lambda: self.player.stop_moving_to(Arrow.down),
        )
        self.keyboard.register_keyaction(
            pygame.K_RIGHT,
            0,
            0,
            lambda: self.player.will_move_to(Arrow.right),
            lambda: self.player.stop_moving_to(Arrow.right),
        )
        self.keyboard.register_keyaction(
            pygame.K_LEFT,
            0,
            0,
            lambda: self.player.will_move_to(Arrow.left),
            lambda: self.player.stop_moving_to(Arrow.left),
        )
        self.keyboard.register_keyaction(
            pygame.K_z, 0, 4, self.player.shooting, self.player.on_release_trigger
        )
        self.keyboard.register_keyaction(pygame.K_x, 0, 4, self.player.shooting_missile)
        self.keyboard.register_keyaction(pygame.K_c, 0, 10, self.switch_weapon)
        self.keyboard.register_keyaction(pygame.K_v, 0, 10, self.reset_game)

    def switch_weapon(self):
        if self.player.current_weapon == "normal":
            self.player.change_weapon("laser")
        else:
            self.player.change_weapon("normal")

    def update(self, dt):
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.load(music_dict["space_battle"])
            pygame.mixer.music.play()
        textfactory.rewrite_text("gamescore", f"スコア:{self.gameworld.gamescore}")
        textfactory.rewrite_text(
            "highscore", f"ハイスコア:{self.gameworld.highscore()}"
        )
        textfactory.set_text_pos_to_right("highscore")
        textfactory.rewrite_text(
            "num_of_enemy", f"敵機残り:{self.gameworld.num_of_remaining_enemies}"
        )
        textfactory.rewrite_text(
            "elapsed_time_in_level",
            f"経過時間:{round(self.gameworld.elapsed_time_in_level)}",
        )
        textfactory.rewrite_text(
            "count_of_enemies_summoned",
            f"敵生成数:{self.gameworld.count_of_enemies_summoned}",
        )

        self.keyboard.do_action_by_keyinput(pygame.K_v)

        if show_hitbox:
            self.gameworld.show_hitbox()
        else:
            self.gameworld.hide_hitbox()

        if not self.gameworld.pause:
            self.keyboard.do_action_by_keyinput(pygame.K_UP)
            self.keyboard.do_action_by_keyinput(pygame.K_DOWN)
            self.keyboard.do_action_by_keyinput(pygame.K_RIGHT)
            self.keyboard.do_action_by_keyinput(pygame.K_LEFT)
            self.keyboard.do_action_by_keyinput(pygame.K_z)
            self.keyboard.do_action_by_keyinput(pygame.K_x)
            self.keyboard.do_action_by_keyinput(pygame.K_c)
            self.keyboard.do_action_by_keyinput(pygame.K_q)

            self.gameworld.stop_entity_from_moving_off_screen(self.player)

            if self.gameworld.count_of_enemies_summoned > 0:
                if (
                    not (self.player in self.gameworld.entities)
                    or self.gameworld.num_of_remaining_enemies == 0
                ):
                    self.stop_game_and_show_result()

            self.gameworld.run_level(dt)
            self.gameworld.process_collision(
                (self.player,), self.player.shot_que + self.player.missile_que
            )

            self.gameworld.clear_enemies_off_screen()
            self.gameworld.scroll(dt)

    def reset_game(self):
        self.gameworld.pause = False
        self.gameworld.initialize_level()
        self.init_player()
        self.init_text()

    def stop_game_and_show_result(self):
        pygame.mixer.music.load(music_dict["gameover"])
        pygame.mixer.music.play()
        # sound_dict["gameover"].play()
        textfactory.set_text_color("gamescore", [255, 200, 255])
        textfactory.center_text_pos_x("gamescore")
        textfactory.center_text_pos_y("gamescore")
        self.gameworld.pause = True
        self.gameworld.register_gamescore()

    def draw(self, screen):
        screen.blit(
            self.gameworld.bg_surf, (0, self.gameworld.bg_scroll_y - global_.w_size[1])
        )
        textfactory.render("tutorial", screen, (0, 0))
        textfactory.render("highscore", screen)
        textfactory.render("gamescore", screen)
        textfactory.render("num_of_enemy", screen, (0, 48))
        textfactory.render("elapsed_time_in_level", screen, (0, 64))
        textfactory.render("count_of_enemies_summoned", screen, (0, 80))


class OptionsScene(Scene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        textfactory.set_current_font("misaki_gothic")
        textfactory.register_text("enemy_se_volume", "")
        textfactory.register_text("player_se_volume", "")
        textfactory.register_text("switch_hitbox", "")
        textfactory.register_text("se_volume_header", "-Sound Volume-")
        textfactory.register_text("return", "RETURN TO THE MENU")
        textfactory.register_text("menu_cursor_>", ">")
        self.menu_cursor_pos = [0, 16]
        self.arrow_for_menu_cursor = ArrowToTurnToward()
        self.gamemenu = ["enemy_se_volume", "player_se_volume", "hitbox", 0]
        self.index_of_menu_item_selected = 0
        self.keyboard.register_keyaction(pygame.K_UP, 0, 10, self.go_up_menu_cursor)
        self.keyboard.register_keyaction(pygame.K_DOWN, 0, 10, self.go_down_menu_cursor)
        self.keyboard.register_keyaction(pygame.K_z, 0, 20, self.command_menu_item)
        self.keyboard.register_keyaction(
            pygame.K_RIGHT, 0, 10, self.add_value_of_option
        )
        self.keyboard.register_keyaction(pygame.K_LEFT, 0, 10, self.sub_value_of_option)

    def process_menu_cursor(self):
        if self.arrow_for_menu_cursor.is_up:
            self.go_up_menu_cursor()
        elif self.arrow_for_menu_cursor.is_down:
            self.go_down_menu_cursor()

    def go_up_menu_cursor(self):
        if 0 < self.index_of_menu_item_selected:
            self.menu_cursor_pos[1] -= 16
            self.index_of_menu_item_selected -= 1

    def go_down_menu_cursor(self):
        if self.index_of_menu_item_selected < len(self.gamemenu) - 1:
            self.menu_cursor_pos[1] += 16
            self.index_of_menu_item_selected += 1

    def menu_pointed_by_cursor(self):
        return self.gamemenu[self.index_of_menu_item_selected]

    def command_menu_item(self):
        menu_item = self.menu_pointed_by_cursor()
        if isinstance(menu_item, str):
            if menu_item == "hitbox":
                global show_hitbox
                show_hitbox = not show_hitbox
        else:
            self.manager.transition_to(menu_item)

    def add_value_of_option(self):
        menu_item = self.menu_pointed_by_cursor()
        if menu_item == "enemy_se_volume":
            channel_manager["enemy"]["volume"] += 0.1
        if menu_item == "player_se_volume":
            channel_manager["player"]["volume"] += 0.1

    def sub_value_of_option(self):
        menu_item = self.menu_pointed_by_cursor()
        if menu_item == "enemy_se_volume":
            channel_manager["enemy"]["volume"] -= 0.1
        if menu_item == "player_se_volume":
            channel_manager["player"]["volume"] -= 0.1

    def update(self, dt):
        textfactory.rewrite_text(
            "enemy_se_volume",
            "Enemy: " + str(round(channel_manager["enemy"]["volume"], 1)),
        )
        textfactory.rewrite_text(
            "player_se_volume",
            "Player: " + str(round(channel_manager["player"]["volume"], 1)),
        )
        textfactory.rewrite_text("switch_hitbox", f"Show hitbox: {show_hitbox}")
        self.keyboard.do_action_by_keyinput(pygame.K_UP)
        self.keyboard.do_action_by_keyinput(pygame.K_DOWN)
        self.keyboard.do_action_by_keyinput(pygame.K_RIGHT)
        self.keyboard.do_action_by_keyinput(pygame.K_LEFT)
        self.keyboard.do_action_by_keyinput(pygame.K_z)
        self.process_menu_cursor()

    def draw(self, screen):
        textfactory.render("se_volume_header", screen, (16, 0))
        textfactory.render("enemy_se_volume", screen, (16, 16))
        textfactory.render("player_se_volume", screen, (16, 32))
        textfactory.render("switch_hitbox", screen, (16, 48))
        textfactory.render("return", screen, (16, 64))
        textfactory.render("menu_cursor_>", screen, self.menu_cursor_pos)


class TitleMenuScene(Scene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joystick = Joystick2(joystick)
        textfactory.set_current_font("misaki_gothic")
        textfactory.register_text("title_start", "START")
        textfactory.register_text("title_options", "OPTIONS")
        textfactory.register_text("title_exit", "EXIT")
        textfactory.register_text("menu_cursor_>", ">")
        self.menu_cursor_pos = [0, 0]
        self.gamemenu = [2, 1, -1]
        self.index_of_menu_item_selected = 0
        self.keyboard.register_keyaction(pygame.K_UP, 0, 10, self.go_up_menu_cursor)
        self.keyboard.register_keyaction(pygame.K_DOWN, 0, 10, self.go_down_menu_cursor)
        self.keyboard.register_keyaction(pygame.K_z, 0, 20, self.command_menu_item)
        self.gamemenuui = UIBoxLayout()
        self.ui_text_start = UIElement()
        self.ui_text_option = UIElement()
        self.ui_text_ex = UIElement()

    def process_menu_cursor(self):
        if self.arrow_for_menu_cursor.is_up:
            self.go_up_menu_cursor()
        elif self.arrow_for_menu_cursor.is_down:
            self.go_down_menu_cursor()

    def go_up_menu_cursor(self):
        if 0 < self.index_of_menu_item_selected:
            self.menu_cursor_pos[1] -= 16
            self.index_of_menu_item_selected -= 1

    def go_down_menu_cursor(self):
        if self.index_of_menu_item_selected < len(self.gamemenu) - 1:
            self.menu_cursor_pos[1] += 16
            self.index_of_menu_item_selected += 1

    def command_menu_item(self):
        self.manager.transition_to(self.gamemenu[self.index_of_menu_item_selected])

    def update(self, dt):
        self.keyboard.do_action_by_keyinput(pygame.K_UP)
        self.keyboard.do_action_by_keyinput(pygame.K_DOWN)
        self.keyboard.do_action_by_keyinput(pygame.K_z)

    def draw(self, screen):
        textfactory.render("title_start", screen, (16, 0))
        textfactory.render("title_options", screen, (16, 16))
        textfactory.render("title_exit", screen, (16, 32))
        textfactory.render("menu_cursor_>", screen, self.menu_cursor_pos)


class UIDebugScene(Scene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.testui = UIBoxLayout()
        self.ui1 = UIElement(pygame.surface.Surface((32, 32)))
        self.ui1.surface.fill((255, 255, 0))
        self.ui2 = UIElement(pygame.surface.Surface((26, 32)))
        self.ui2.surface.fill((0, 255, 0))
        self.ui3 = UIGameText(textfactory.font(), "test1")
        self.ui4 = UIGameText(textfactory.font(), "test2")
        # print(self.ui1.height)
        self.testui.add_ui_element(self.ui1)
        self.testui.add_ui_element(self.ui2)
        self.testui.add_ui_element(self.ui3)
        self.testui.add_ui_element(self.ui4)
        self.testui.spacing = 20
        self.testui.x = 10
        self.testui.y = 20

    def draw(self, screen):
        self.testui.draw(screen)
        # self.ui1.draw(screen)


def run(fps_num=fps):
    global fps
    fps = fps_num
    running = True
    scene_manager = SceneManager()
    scene_manager.push(TitleMenuScene(scene_manager))
    scene_manager.push(OptionsScene(scene_manager))
    scene_manager.push(GameScene(scene_manager))
    scene_manager.push(UIDebugScene(scene_manager))
    # scene_manager.transition_to(3)
    while running:
        dt = clock.tick(fps) / 1000  # dt means delta time

        global_.screen.fill((0, 0, 0))
        for event in pygame.event.get():
            running = scene_manager.event(event)

        scene_manager.update(dt)
        scene_manager.draw(global_.screen)
        pygame.transform.scale(
            global_.screen, global_.w_size_unscaled, pygame.display.get_surface()
        )
        pygame.display.update()
        IntervalCounter.tick(dt)
    pygame.quit()
