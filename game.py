# Import necessary libraries
import os
import sys
import math
import random

# Import the pygame library for game development
import pygame

# Import custom utility functions and classes from other scripts
from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Enemy
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark

# The Game class controls the main logic and flow of the game
class Game:
    def __init__(self):
        # Initialize pygame
        pygame.init()

        # Set up the game window and screen
        pygame.display.set_caption('ShadowStrike')  # Title of the window
        self.screen = pygame.display.set_mode((640, 480))  # Main screen resolution
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA)  # Smaller surface for rendering
        self.display_2 = pygame.Surface((320, 240))  # Another surface for rendering

        # Set up the game clock for controlling the frame rate
        self.clock = pygame.time.Clock()
        
        # Movement controls for the player (example: left, right)
        self.movement = [False, False]
        
        # Load the game assets (images, sounds, animations)
        self.assets = {
            'decor': load_images('tiles/decor'),  # Decorative tiles for the environment
            'grass': load_images('tiles/grass'),  # Grass tiles for the environment
            'large_decor': load_images('tiles/large_decor'),  # Larger decorative tiles
            'stone': load_images('tiles/stone'),  # Stone tiles for the environment
            'player': load_image('entities/player.png'),  # Player character image
            'background': load_image('background.png'),  # Background image
            'clouds': load_images('clouds'),  # Cloud images for atmospheric effect
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),  # Enemy idle animation
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),  # Enemy running animation
            'player/idle': Animation(load_images('entities/player/idle'), img_dur=6),  # Player idle animation
            'player/run': Animation(load_images('entities/player/run'), img_dur=4),  # Player running animation
            'player/jump': Animation(load_images('entities/player/jump')),  # Player jumping animation
            'player/slide': Animation(load_images('entities/player/slide')),  # Player sliding animation
            'player/wall_slide': Animation(load_images('entities/player/wall_slide')),  # Player wall sliding animation
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),  # Leaf particle animation
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),  # General particle animation
            'gun': load_image('gun.png'),  # Gun image for the player
            'projectile': load_image('projectile.png'),  # Projectile image for the player's weapon
        }
        
        # Sound effects for various actions in the game
        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),  # Jump sound
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),  # Dash sound
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),  # Hit sound
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),  # Shoot sound
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav'),  # Background ambience sound
        }
        
        # Set volumes for each sound effect to customize audio experience
        self.sfx['ambience'].set_volume(0.2)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['dash'].set_volume(0.3)
        self.sfx['jump'].set_volume(0.7)
        
        # Set up clouds in the game using the cloud assets
        self.clouds = Clouds(self.assets['clouds'], count=16)
        
        # Initialize the player object
        self.player = Player(self, (50, 50), (8, 15))
        
        # Initialize the tilemap (level layout)
        self.tilemap = Tilemap(self, tile_size=16)
        
        # Initialize the level and load the first one
        self.level = 0
        self.load_level(self.level)
        
        # Variable to control screen shake effect
        self.screenshake = 0
        
    def load_level(self, map_id):
        # Load a map based on the given map_id
        self.tilemap.load('data/maps/' + str(map_id) + '.json')
        
        # Initialize leaf spawners (objects that spawn leaf particles)
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
            
        # Initialize enemies (from spawners in the level)
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))
            
        # Initialize empty lists for projectiles, particles, and sparks
        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        # Initialize the scrolling position and other level properties
        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30
        
    def run(self):
        # Start playing the background music
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        
        # Play the ambient sound effect in a loop
        self.sfx['ambience'].play(-1)
        
        # Main game loop
        while True:
            # Clear the display for the next frame
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))  # Draw the background image
            
            # Update the screenshake effect (if applicable)
            self.screenshake = max(0, self.screenshake - 1)
            
            # Handle level transition if all enemies are defeated
            if not len(self.enemies):
                self.transition += 1
                if self.transition > 30:
                    # Load the next level if available
                    self.level = min(self.level + 1, len(os.listdir('data/maps')) - 1)
                    self.load_level(self.level)
            if self.transition < 0:
                self.transition += 1
            
            # Handle player death and respawn logic
            if self.dead:
                self.dead += 1
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                if self.dead > 40:
                    self.load_level(self.level)
            
            # Update scrolling to keep the player centered on the screen
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            
            # Loop through leaf spawners to randomly create leaf particles
            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    # Randomly generate position within the spawner's rectangle
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    # Add a new leaf particle with initial position and random frame
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            # Update and render clouds in the background
            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll)

            # Render the tilemap (background and tiles) with scroll offset
            self.tilemap.render(self.display, offset=render_scroll)

            # Update and render each enemy
            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))  # Update enemy state
                enemy.render(self.display, offset=render_scroll)  # Render enemy
                if kill:  # If enemy is killed, remove it from the list
                    self.enemies.remove(enemy)

            # If the player is not dead, update and render the player
            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            # Handle projectiles (like bullets)
            for projectile in self.projectiles.copy():
                # Move the projectile and increment timer
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                # Render the projectile on the screen
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                
                # Check for collisions with solid tiles
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for i in range(4):  # Create sparks on collision
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                
                # Check if the projectile has traveled too far (360 frames)
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                
                # Check for collision with player (if the player is dashing)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().collidepoint(projectile[0]):
                        self.projectiles.remove(projectile)
                        self.dead += 1  # Player is hit and dies
                        self.sfx['hit'].play()  # Play hit sound effect
                        self.screenshake = max(16, self.screenshake)  # Trigger screenshake effect
                        # Create sparks and particles on player hit
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))

            # Update and render each spark (visual effect)
            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:  # Remove spark if it is no longer active
                    self.sparks.remove(spark)

            # Create a shadow silhouette for the player and enemies on the screen
            display_mask = pygame.mask.from_surface(self.display)
            display_sillhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_sillhouette, offset)

            # Update and render each particle (like leaves or general effects)
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                # Make the leaf particles move in a sine wave pattern for a fluttering effect
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:  # Remove particle if it is no longer active
                    self.particles.remove(particle)

            # Event handling (keyboard input and quitting)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()  # Quit the game
                    sys.exit()  # Exit the program
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.movement[0] = True  # Move player left
                    if event.key == pygame.K_RIGHT:
                        self.movement[1] = True  # Move player right
                    if event.key == pygame.K_UP:
                        if self.player.jump():  # Make the player jump
                            self.sfx['jump'].play()  # Play jump sound effect
                    if event.key == pygame.K_x:
                        self.player.dash()  # Make the player dash
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT:
                        self.movement[0] = False  # Stop moving left
                    if event.key == pygame.K_RIGHT:
                        self.movement[1] = False  # Stop moving right

            # Transition effect (when moving between levels or after death)
            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255))  # Set transparency for transition circle
                self.display.blit(transition_surf, (0, 0))

            # Blit the final display onto the secondary surface
            self.display_2.blit(self.display, (0, 0))

            # Apply screenshake effect by shifting the display randomly
            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)

            # Update the display and control the frame rate
            pygame.display.update()
            self.clock.tick(60)  # Limit to 60 frames per second

# Start the game loop by calling the run method
Game().run()