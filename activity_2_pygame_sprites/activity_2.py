# Activity 2: Interactive Game Architecture - Game Loop, Custom Sprites, & Collision Detection
# Computer Graphics Programming Laboratory
#
# Classic game loop: Process Input -> Update Game State -> Render Display -> Regulate FPS.
# Rendering is kept OUT of sprite.update(): sprites only mutate their own state, while
# all blitting happens in the render stage of the main loop (separation of concerns).

import math
import random
import sys

import pygame

# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
WINDOW_TITLE = 'Activity 2: Sprite System & Collision Arena'
BACKGROUND_COLOR = (18, 24, 38)
HUD_TEXT_COLOR = (235, 240, 255)

PLAYER_COLOR = (44, 94, 138)        # steel blue circle, 40x40
OBSTACLE_COLOR = (220, 50, 50)      # red-ish square, 30x30
PARTICLE_COLORS = [(255, 120, 120), (255, 200, 120), (140, 200, 255), (200, 255, 200)]

PLAYER_SIZE = 40
OBSTACLE_SIZE = 30
OBSTACLE_COUNT = 8
PARTICLES_PER_HIT = 14
MAX_PARTICLES = 300                 # hard cap so a collision storm cannot leak sprites
STARTING_HEALTH = 10


# ---------------------------------------------------------------------------
# Sprite classes
# ---------------------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    """Player-controlled circle steered with continuous keyboard input.

    update() mutates state only (position + clamping). No rendering happens
    here: the main loop calls group.draw(screen), keeping concerns separated.
    """

    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(
            self.image, PLAYER_COLOR,
            (PLAYER_SIZE // 2, PLAYER_SIZE // 2), PLAYER_SIZE // 2
        )
        self.rect = self.image.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        )
        self.speed = 5

    def update(self):
        """Continuous steering via pygame.key.get_pressed() with strict clamping."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += self.speed
        if keys[pygame.K_UP] and self.rect.top > 0:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += self.speed
        # Strict boundary clamping: never allow even a 1 px overshoot.
        self.rect.left = max(self.rect.left, 0)
        self.rect.top = max(self.rect.top, 0)
        self.rect.right = min(self.rect.right, SCREEN_WIDTH)
        self.rect.bottom = min(self.rect.bottom, SCREEN_HEIGHT)


class Obstacle(pygame.sprite.Sprite):
    """Roaming red square that moves with random velocity and bounces off edges."""

    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((OBSTACLE_SIZE, OBSTACLE_SIZE), pygame.SRCALPHA)
        self.image.fill(OBSTACLE_COLOR)
        pygame.draw.rect(
            self.image, (255, 120, 120),
            (4, 4, OBSTACLE_SIZE - 8, OBSTACLE_SIZE - 8), border_radius=6
        )
        self.rect = self.image.get_rect(
            topleft=(
                random.randint(0, SCREEN_WIDTH - OBSTACLE_SIZE),
                random.randint(0, SCREEN_HEIGHT - OBSTACLE_SIZE),
            )
        )
        self.velocity = self.random_velocity()

    @staticmethod
    def random_velocity():
        """Uniformly random direction, speed in [3.0, 6.0] px per frame."""
        angle = random.uniform(0.0, 2.0 * math.pi)
        speed = random.uniform(3.0, 6.0)
        return [speed * math.cos(angle), speed * math.sin(angle)]

    def update(self):
        """Move, then bounce off the four screen edges."""
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        if self.rect.left <= 0:
            self.rect.left = 0
            self.velocity[0] = abs(self.velocity[0])
        elif self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.velocity[0] = -abs(self.velocity[0])
        if self.rect.top <= 0:
            self.rect.top = 0
            self.velocity[1] = abs(self.velocity[1])
        elif self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.velocity[1] = -abs(self.velocity[1])


class Particle(pygame.sprite.Sprite):
    """Short-lived translucent impact particle drawn on a pygame.SRCALPHA surface.

    Fading uses per-surface alpha (Surface.set_alpha) that decreases over time;
    each particle owns its own surface so alphas do not interfere.
    """

    def __init__(self, x, y):
        super().__init__()
        self.radius = random.randint(3, 7)
        self.base_color = random.choice(PARTICLE_COLORS)
        self.lifetime = random.randint(18, 30)   # frames
        self.age = 0
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, self.base_color, (self.radius, self.radius), self.radius)
        self.image.set_alpha(255)
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0.0, 2.0 * math.pi)
        speed = random.uniform(1.0, 4.0)
        self.velocity = [speed * math.cos(angle), speed * math.sin(angle)]

    def update(self):
        """Drift outward and fade: set_alpha decreases linearly over the lifetime."""
        self.age += 1
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        self.image.set_alpha(max(0, 255 - int(255 * self.age / self.lifetime)))
        if self.age >= self.lifetime or self.image.get_alpha() <= 0:
            self.kill()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def spawn_particles(group, x, y, count=PARTICLES_PER_HIT):
    """Spawn translucent impact particles at (x, y) into a managed sprite group."""
    for _ in range(count):
        if len(group) < MAX_PARTICLES:
            group.add(Particle(x, y))


def update_hud(screen, score, health, fps, font):
    """Render the live HUD (Score / Health / FPS) with an anti-aliased font.

    The pygame.font.Font object is created ONCE in main() and passed in every
    frame, so the HUD never allocates fonts per frame (no memory leak).
    """
    for i, text in enumerate(("Score: {}".format(score),
                              "Health: {}".format(health),
                              "FPS: {:.0f}".format(fps))):
        surface = font.render(text, True, HUD_TEXT_COLOR)
        screen.blit(surface, (10, 10 + i * 30))


def draw_arena(screen):
    """Render stage background; sprites and HUD are blitted afterwards."""
    screen.fill(BACKGROUND_COLOR)


def respawn_away_from_player(obstacle, player, min_distance=80):
    """Move an obstacle to a fresh random position away from the player and
    give it a new random velocity (dynamic respawn on collision)."""
    guard = 0
    while guard < 1000 and (
        obstacle.rect.colliderect(player.rect)
        or (abs(obstacle.rect.centerx - player.rect.centerx) < min_distance
            and abs(obstacle.rect.centery - player.rect.centery) < min_distance)
    ):
        obstacle.rect.topleft = (
            random.randint(0, SCREEN_WIDTH - OBSTACLE_SIZE),
            random.randint(0, SCREEN_HEIGHT - OBSTACLE_SIZE),
        )
        guard += 1
    obstacle.velocity = Obstacle.random_velocity()


# ---------------------------------------------------------------------------
# Game container: owns all state shared by the four game-loop stages
# ---------------------------------------------------------------------------
class Game:
    """Holds every mutable piece of game state so main() stays a thin loop."""

    def __init__(self):
        self.player = Player()
        self.player_group = pygame.sprite.GroupSingle(self.player)
        self.obstacles = pygame.sprite.Group(
            *[Obstacle() for _ in range(OBSTACLE_COUNT)]
        )
        self.particles = pygame.sprite.Group()
        self.score = 0
        self.health = STARTING_HEALTH
        self.font = pygame.font.Font(None, 36)   # created once, reused forever

    def process_events(self):
        """Stage 1: process input events; returns False when the loop must end."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def update_state(self):
        """Stage 2: update all sprites, then resolve player/obstacle collisions."""
        self.player_group.update()
        self.obstacles.update()
        self.particles.update()

        hits = pygame.sprite.spritecollide(
            self.player, self.obstacles, False, pygame.sprite.collide_rect
        )
        for obstacle in hits:
            self.score += 1
            self.health -= 1
            spawn_particles(self.particles,
                            obstacle.rect.centerx, obstacle.rect.centery)
            respawn_away_from_player(obstacle, self.player)

    def render(self, screen, fps):
        """Stage 3: render display (all blitting lives here, never in sprites)."""
        draw_arena(screen)
        self.obstacles.draw(screen)
        self.particles.draw(screen)
        self.player_group.draw(screen)
        update_hud(screen, self.score, self.health, fps, self.font)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    game = Game()
    last_fps = 0.0

    running = True
    while running:
        # --- 1. Process input ------------------------------------------------
        running = game.process_events()

        # --- 2. Update game state ---------------------------------------------
        game.update_state()

        # --- 3. Render display -------------------------------------------------
        game.render(screen, clock.get_fps())
        pygame.display.flip()

        # --- 4. Regulate FPS ----------------------------------------------------
        clock.tick(FPS)

    pygame.quit()
    return 0


if __name__ == '__main__':
    sys.exit(main())
