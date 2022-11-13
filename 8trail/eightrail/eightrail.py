from .utilities import Arrow, AssetFilePath, TextToDebug  # noqa
from .schedule import IntervalCounter, schedule_instance_method_interval
from .gamelevel import Level
from .gamescene import Scene, SceneManager
from .entity import Sprite, ShooterSprite

import pygame

from .animation import (
    AnimationDict, AnimationImage, AnimationFactory, SpriteSheet
)

from .__init__ import init, w_size, screen, w_size_unscaled  # noqa

# TODO: Game Level

pygame.init()

clock = pygame.time.Clock()
fps = 60


class Explosion(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("explosion_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 16, 16),
            self.sprite_sheet.image_by_area(
                0, 16, 16, 16),
            self.sprite_sheet.image_by_area(
                0, 16*2, 16, 16),
            self.sprite_sheet.image_by_area(
                0, 16*3, 16, 16),
            self.sprite_sheet.image_by_area(
                0, 16*4, 16, 16),
            self.sprite_sheet.image_by_area(0, 16*5, 16, 16)]
        self.anim_interval = 2


class PlayerExplosion(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("explosion_b.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 22, 22),
            self.sprite_sheet.image_by_area(
                0, 22, 22, 22),
            self.sprite_sheet.image_by_area(
                0, 22*2, 22, 22),
            self.sprite_sheet.image_by_area(
                0, 22*3, 22, 22),
            self.sprite_sheet.image_by_area(
                0, 22*4, 22, 22),
            self.sprite_sheet.image_by_area(0, 22*5, 22, 22)]
        self.anim_interval = 2


class FighterIdle(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 22 * 2, 22, 22), ]


class FighterRollLeft(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 0, 22, 22),
            self.sprite_sheet.image_by_area(0, 22, 22, 22), ]
        self.anim_interval = 15
        self.is_loop = False


class FighterRollRight(AnimationImage):
    def __init__(self):
        super().__init__()
        self.sprite_sheet = SpriteSheet(AssetFilePath.img("fighter_a.png"))
        self.anim_frames: list[pygame.surface.Surface] = [
            self.sprite_sheet.image_by_area(0, 22 * 3, 22, 22),
            self.sprite_sheet.image_by_area(0, 22 * 4, 22, 22), ]
        self.anim_interval = 15
        self.is_loop = False
        # self.rect = self.image.get_rect()


class PlayerShot(Sprite):
    def __init__(self, shooter_sprite: ShooterSprite,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = pygame.image.load(AssetFilePath.img("shot1.png"))
        self.shooter = shooter_sprite
        self.rect = self.image.get_rect()
        self.reset_pos()
        self.movement_speed = 4
        self.adjust_movement_speed = 1
        self.is_launching = False
        self.kill()

    def reset_pos(self):
        self.x = self.shooter.x + \
            self.shooter.rect.width / 2 - self.rect.width / 2
        self.y = self.shooter.y + \
            self.shooter.rect.height / 2 - self.rect.height

    def will_launch(self, direction: Arrow):
        self.direction_of_movement.set(direction)
        self.entity_container.append(self)
        self.is_launching = True
        # set accelerater if the direction is the same as that of the shooter.
        if (self.direction_of_movement.is_up and
                self.shooter.direction_of_movement.is_up):
            self.adjust_movement_speed = self.shooter.movement_speed
        else:
            self.adjust_movement_speed = 0

    def _fire(self, dt):
        if self.is_launching:
            self.move_on(dt)
            if self.y < 0:
                self.direction_of_movement.unset(Arrow.up)
                self.is_launching = False
                self.reset_pos()
                self.allow_shooter_to_fire()
                self._destruct()

    def _destruct(self):
        """Remove sprite from group and que of shooter."""
        self.shooter.shot_que.remove(self)
        self.entity_container.kill_living_entity(self)
        self.is_launching = False

    def allow_shooter_to_fire(self):
        self.shooter.is_shot_allowed = True

    def draw(self, screen: pygame.surface.Surface):
        screen.blit(self.image, self.rect)

    def update(self, dt):
        if not self.is_launching:
            self.reset_pos()
        self._fire(dt)

    def collide(self, sprite):
        if pygame.sprite.collide_rect(self, sprite):
            self._destruct()


class Enemy(Sprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.explosion_sound = pygame.mixer.Sound(
            AssetFilePath.sound("explosion1.wav"))
        self.image = pygame.image.load(AssetFilePath.img("enemy_a.png"))
        self.rect = self.image.get_rect()
        self.animation = AnimationFactory()
        self.animation["death"] = Explosion

    def draw(self, screen: pygame.surface.Surface):
        screen.blit(self.image, self.rect)

    def death(self):
        animation = self.animation["death"]
        animation.rect = self.rect
        animation.let_play_animation()
        self.gameworld.scene.visual_effects.append(animation)
        self.entity_container.kill_living_entity(self)
        self.explosion_sound.play()

    def collide_with_shot(self, shot):
        if pygame.sprite.collide_rect(shot, self):
            self.death()


class Player(ShooterSprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.animation = AnimationDict()
        self.animation["idle"] = FighterIdle()
        self.animation["roll_left"] = FighterRollLeft()
        self.animation["roll_right"] = FighterRollRight()
        self.visual_effects = AnimationFactory()
        self.visual_effects["explosion"] = PlayerExplosion
        self.explosion_sound = pygame.mixer.Sound(
            AssetFilePath.sound("explosion1.wav"))
        self.action = "idle"
        self.image = self.animation[self.action].image
        self.rect = self.image.get_rect()
        self.movement_speed = 2
        self.shot_max_num = 3
        self.shot_interval = 3
        self.shot_current_interval = self.shot_interval
        self.shot_que: list = []
        self.ignore_shot_interval = True
        self.is_shot_triggered = False
        self.is_moving = True
        self.shot_sound = pygame.mixer.Sound(AssetFilePath.sound("shot1.wav"))

    def trigger_shot(self):
        self.is_shot_triggered = True

    def release_trigger(self):
        self.is_shot_triggered = False

    @ schedule_instance_method_interval(
        "shot_current_interval", interval_ignorerer="ignore_shot_interval")
    def _shooting(self):
        if (self.is_shot_allowed and (len(self.shot_que) < self.shot_max_num)):
            self.shot_sound.play()
            shot = PlayerShot(self)
            shot.entity_container = self.entity_container
            shot.will_launch(Arrow.up)
            self.shot_que.append(shot)

    def will_move_to(self, direction: Arrow):
        self.direction_of_movement.set(direction)
        if self.direction_of_movement.is_left:
            self.action = "roll_left"
        elif self.direction_of_movement.is_right:
            self.action = "roll_right"
        if not self.is_moving:
            self.animation[self.action].let_play_animation()
        self.is_moving = True

    def stop_moving_to(self, direction: Arrow):
        self.direction_of_movement.unset(direction)
        if not self.direction_of_movement.is_set_any():
            self.action = "idle"
            self.is_moving = False

    def draw(self, screen: pygame.surface.Surface):
        screen.blit(self.image, self.rect)

    def update(self, dt):
        if self.is_moving:
            self.move_on(dt)
        if self.shot_que:
            self.is_shooting = True
            self.ignore_shot_interval = False
        else:
            self.is_shooting = False
            self.ignore_shot_interval = True
        if self.is_shot_triggered:
            self._shooting()
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
            self.explosion_sound.play()

    def collide_with_enemy(self, enemy: Enemy):
        if not isinstance(enemy, Enemy):
            raise TypeError("Given entity is not Enemy.")
        if pygame.sprite.collide_rect(enemy, self):
            self.death()


class GameScene(Scene):

    gamefont = pygame.font.Font(AssetFilePath.font("misaki_gothic.ttf"), 16)
    instruction_text = gamefont.render(
        "z: ショット x: 敵を再召喚 c:自機を復活させる", True, (255, 255, 255))

    def __init__(self):
        super().__init__()
        self.gameworld = Level(AssetFilePath.level("stage1.json"), self)
        self.gameworld.set_background()
        self.gameworld.enemy_factory["scoutdisk"] = Enemy
        self.player = Player(self.gameworld.entities)
        self.player.center_x_on_screen()
        self.player.y = w_size[1] - self.player.rect.height
        # self.player.entity_container = self.gameworld.entities
        self.gameworld.entities.append(self.player)

    def event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.player.will_move_to(Arrow.up)
            if event.key == pygame.K_DOWN:
                self.player.will_move_to(Arrow.down)
            if event.key == pygame.K_RIGHT:
                self.player.will_move_to(Arrow.right)
            if event.key == pygame.K_LEFT:
                self.player.will_move_to(Arrow.left)
            if event.key == pygame.K_z:
                self.player.trigger_shot()
            if event.key == pygame.K_x:
                self.gameworld.summon_enemies_with_timing_resetted()
            if event.key == pygame.K_c:
                if self.player not in self.gameworld.entities:
                    self.gameworld.entities.append(self.player)
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_UP:
                self.player.stop_moving_to(Arrow.up)
            if event.key == pygame.K_DOWN:
                self.player.stop_moving_to(Arrow.down)
            if event.key == pygame.K_RIGHT:
                self.player.stop_moving_to(Arrow.right)
            if event.key == pygame.K_LEFT:
                self.player.stop_moving_to(Arrow.left)
            if event.key == pygame.K_z:
                self.player.release_trigger()

    def stop_move_of_player_on_wall(self):
        if self.player.y < 0:
            self.player.stop_moving_to(Arrow.up)
        if w_size[1] - self.player.rect.height < self.player.y:
            self.player.stop_moving_to(Arrow.down)
        if w_size[0] - self.player.rect.width < self.player.x:
            self.player.stop_moving_to(Arrow.right)
        if self.player.x < 0:
            self.player.stop_moving_to(Arrow.left)

    def update(self, dt):
        for enemy in self.gameworld.enemies:
            for shot in self.player.shot_que:
                enemy.collide_with_shot(shot)
                shot.collide(enemy)
            self.player.collide_with_enemy(enemy)
        self.stop_move_of_player_on_wall()
        self.gameworld.run_level()
        self.gameworld.scroll()

    def draw(self, screen):
        screen.blit(self.gameworld.bg_surf,
                    (0, self.gameworld.bg_scroll_y - w_size[1]))
        screen.blit(self.instruction_text, (0, 0))


class TitleMenuScene(Scene):
    def __init__(self):
        super().__init__()


def run(fps_num=fps):
    global fps
    fps = fps_num
    running = True
    scene_manager = SceneManager()
    # scene_manager.push(TitleMenuScene())
    scene_manager.push(GameScene())
    while running:
        dt = clock.tick(fps)/1000  # dt means delta time

        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            scene_manager.event(event)
        scene_manager.update(dt)
        scene_manager.draw(screen)
        # resize pixel size
        pygame.transform.scale(screen, w_size_unscaled,
                               pygame.display.get_surface())
        pygame.display.update()
        IntervalCounter.tick(dt)
    pygame.quit()
