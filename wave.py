import pygame
import os

class Wave:
    def __init__(self, x, y, speed, inverted=False):
        self.start_x = x
        self.start_y = y
        self.base_speed = speed
        self.inverted = inverted 
        self.reset() 

    def reset(self):
        self.image_size = 60   
        self.hitbox_size = 20  # Hitbox pequeña para precisión
        
        self.rect = pygame.Rect(self.start_x, self.start_y, self.hitbox_size, self.hitbox_size)
        self.speed = self.base_speed
        self.vel_y = 0
        self.holding_jump = False 
        self.trail = []
        self.is_mini = False
        self.current_gravity_inverted = self.inverted
        
        self.update_visuals()

    def update_size_and_hitbox(self):
        if self.is_mini:
            self.image_size = 30; self.hitbox_size = 10
        else:
            self.image_size = 60; self.hitbox_size = 20
            
        center = self.rect.center
        self.rect = pygame.Rect(0, 0, self.hitbox_size, self.hitbox_size)
        self.rect.center = center

    def update_visuals(self):
        if self.inverted:
            self.trail_color = (255, 0, 128); self.color = (255, 0, 128); base_img_name = "wave_dual.png"
        else:
            self.trail_color = (0, 255, 255); self.color = (0, 255, 255); base_img_name = "wave.png"

        self.trail_width = 4 if self.is_mini else 8 
        self.image = None
        try:
            img_path = os.path.join("assets", base_img_name)
            loaded_img = pygame.image.load(img_path).convert_alpha()
            self.original_image = pygame.transform.smoothscale(loaded_img, (self.image_size, self.image_size))
            if self.current_gravity_inverted:
                self.original_image = pygame.transform.flip(self.original_image, False, True)
            self.image = self.original_image
        except: pass

    def set_mode(self, inverted):
        if self.inverted != inverted:
            self.inverted = inverted
            if not inverted: self.current_gravity_inverted = False 
            self.update_visuals()

    def set_gravity(self, inverted):
        if self.current_gravity_inverted != inverted:
            self.current_gravity_inverted = inverted
            self.update_visuals()

    def set_mini(self, mini):
        if self.is_mini != mini:
            self.is_mini = mini
            self.update_size_and_hitbox()
            self.update_visuals()

    def set_speed(self, new_speed): self.speed = new_speed

    def handle_input(self):
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        if keys[pygame.K_SPACE] or keys[pygame.K_UP] or mouse[0]: self.holding_jump = True
        else: self.holding_jump = False

    def update(self, map_speed):
        # Física: La mini wave sube 1.5 veces más rápido en relación a X
        effective_speed = self.speed * 1.5 if self.is_mini else self.speed
        
        if self.current_gravity_inverted:
            self.vel_y = effective_speed if self.holding_jump else -effective_speed
        else:
            self.vel_y = -effective_speed if self.holding_jump else effective_speed
        
        self.rect.y += self.vel_y
        if self.rect.top < 0: self.rect.top = 0
        if self.rect.bottom > 1080: self.rect.bottom = 1080
            
        for point in self.trail: point[0] -= map_speed
        self.trail.append([self.rect.centerx, self.rect.centery])
        self.trail = [p for p in self.trail if p[0] > 0]

    def draw(self, window):
        if len(self.trail) > 1:
            pygame.draw.lines(window, self.trail_color, False, self.trail, self.trail_width)

        if self.image:
            angle = 0
            on_ceiling, on_floor = self.rect.top <= 0, self.rect.bottom >= 1080
            is_sliding = False
            
            if self.current_gravity_inverted:
                if not self.holding_jump and on_ceiling: is_sliding = True
                if self.holding_jump and on_floor: is_sliding = True
            else:
                if self.holding_jump and on_ceiling: is_sliding = True
                if not self.holding_jump and on_floor: is_sliding = True
            
            if not is_sliding:
                # ÁNGULO MATEMÁTICO EXACTO: ~56 grados para mini (atan(1.5))
                base_angle = 56 if self.is_mini else 45
                if self.current_gravity_inverted: angle = -base_angle if self.holding_jump else base_angle
                else: angle = base_angle if self.holding_jump else -base_angle
            
            rotated_img = pygame.transform.rotate(self.original_image, angle)
            new_rect = rotated_img.get_rect(center=self.rect.center)
            window.blit(rotated_img, new_rect.topleft)
        else:
            pygame.draw.rect(window, self.color, self.rect)