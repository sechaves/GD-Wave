import pygame
import tkinter as tk
import threading
import map  
import wave 
import os
import ctypes 

# =============================================================================
#   JUEGO PRINCIPAL
# =============================================================================
def run_game():
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass 

    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("Wave")
    
    WIDTH, HEIGHT = 1920, 1080
    FPS = 60
    DEFAULT_SPEED = 12
    DEATH_DELAY = 700
    GOD_MODE = False  
    
    # Posición inicial
    PLAYER_START_X = int(WIDTH * 0.35)
    
    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
    clock = pygame.time.Clock()
    
    music_loaded = False 
    try:
        music_path = os.path.join("assets", "10000.mp3")
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.5)
        music_loaded = True 
    except: pass

    textures = {} 
    def load_texture(key, filename, color_fallback, custom_size=None):
        try:
            full_path = os.path.join("assets", filename)
            img = pygame.image.load(full_path).convert_alpha()
            target_size = custom_size if custom_size else (30, 30)
            img = pygame.transform.smoothscale(img, target_size)
            textures[key] = img
        except:
            target_size = custom_size if custom_size else (30, 30)
            surf = pygame.Surface(target_size)
            surf.fill(color_fallback)
            textures[key] = surf

    # --- CARGA DE ASSETS ---
    load_texture(9, "negro.png", (0, 0, 0)) 
    load_texture(1, "block_up.png", (0, 255, 0))
    load_texture(2, "block_down.png", (0, 255, 0))
    load_texture(3, "block_up_left.png", (0, 255, 0))
    load_texture(4, "block_up_right.png", (0, 255, 0))
    load_texture(5, "block_down_left.png", (0, 255, 0))
    load_texture(6, "block_down_right.png", (0, 255, 0))
    
    # Rampas (Normales 45°)
    load_texture(7, "subida.png", (255, 0, 0)) 
    load_texture(8, "bajada.png", (0, 0, 255))
    
    # Rampas (Mini 56.3°)
    load_texture(17, "subida_mini.png", (200, 0, 0)) 
    load_texture(18, "bajada_mini.png", (0, 0, 200))
    
    # Portales
    load_texture(10, "portal_dual.png", (255, 165, 0), custom_size=(50, 90))
    load_texture(11, "portal_solo.png", (0, 0, 255), custom_size=(50, 90))
    
    # Velocidad
    load_texture(20, "vel_x0,5.png", (255, 165, 0), custom_size=(50, 90))   
    load_texture(21, "vel_x1.png", (0, 0, 255), custom_size=(50, 90))   
    load_texture(22, "vel_x2.png", (0, 255, 0), custom_size=(50, 90))     
    load_texture(23, "vel_x3.png", (255, 0, 255), custom_size=(50, 90)) 
    load_texture(24, "vel_x4.png", (255, 0, 0), custom_size=(50, 90))  

    # Gravedad
    load_texture(25, "gravity_inverted.png", (255, 255, 0), custom_size=(50,90))
    load_texture(26, "gravity_normal.png", (0, 0, 255), custom_size=(50,90))
    
    # Tamaño
    load_texture(27, "size_mini.png", (255, 0, 255), custom_size=(50,90))
    load_texture(28, "size_normal.png", (0, 255, 0), custom_size=(50,90))

    SPEED_MAP = {20: 9, 21: 12, 22: 15, 23: 19, 24: 24}

    objects = []         
    block_size = 30
    players = [] 
    
    paused, debug_mode, is_dead, game_won = False, False, False, False
    death_time, portal_cooldown = 0, 0
    current_game_speed = DEFAULT_SPEED
    attempts = 1
    distance_traveled, map_total_width_px, attempt_text_x = 0, 0, 0
    
    font_attempts = pygame.font.SysFont("Monserrat", 50, bold=True)
    font_win = pygame.font.SysFont("Monserrat", 100, bold=True)
    font_progress = pygame.font.SysFont("Monserrat", 30, bold=True)
    font_debug = pygame.font.SysFont("Monserrat", 20, bold=True) 

    def reset_level(increment_attempt=True):
        nonlocal is_dead, players, portal_cooldown, current_game_speed, attempts, game_won
        nonlocal map_total_width_px, distance_traveled, attempt_text_x
        
        if increment_attempt: attempts += 1
            
        objects.clear()
        map.group_1_top(0, 0, objects, block_size)
        map.group_1_bot(0, 540, objects, block_size) 
        
        if len(objects) > 0:
            map_total_width_px = 44 * current_game_speed * FPS
        distance_traveled = 0
        attempt_text_x = PLAYER_START_X + 300 
        
        current_game_speed = DEFAULT_SPEED
        main_wave = wave.Wave(PLAYER_START_X, HEIGHT // 2, current_game_speed, inverted=False)
        players = [main_wave]
        
        is_dead, game_won, portal_cooldown = False, False, 0
        
        if music_loaded and pygame.mixer.get_init():
            try: pygame.mixer.music.play(-1)
            except: pass

    # --- SISTEMA DE COLISIÓN POR LÍNEAS ---
    def check_precise_collision(player_rect, tile_rect, tile_type):
        if tile_type not in [7, 8, 17, 18]: 
            kill_box = pygame.Rect(0, 0, 6, 6)
            kill_box.center = player_rect.center
            return kill_box.colliderect(tile_rect)
            
        start_pos = None
        end_pos = None
        
        if tile_type == 7: # / Normal
            start_pos, end_pos = tile_rect.bottomleft, tile_rect.topright
        elif tile_type == 8: # \ Normal
            start_pos, end_pos = tile_rect.topleft, tile_rect.bottomright
        elif tile_type == 17: # / Mini
            start_pos = tile_rect.bottomleft
            end_pos = (tile_rect.left + 20, tile_rect.top)
        elif tile_type == 18: # \ Mini
            start_pos = tile_rect.topleft
            end_pos = (tile_rect.left + 20, tile_rect.bottom)
            
        if start_pos and end_pos:
            if player_rect.clipline(start_pos, end_pos): return True
        return False

    reset_level(increment_attempt=False) 

    run = True
    while run:
        clock.tick(FPS)
        window.fill((0, 0, 0)) 
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: run = False
                if event.key == pygame.K_ESCAPE:
                    if not is_dead and not game_won:
                        paused = not paused
                        if music_loaded:
                            if paused: pygame.mixer.music.pause()
                            else: pygame.mixer.music.unpause()
                if event.key == pygame.K_r:
                    reset_level(increment_attempt=True)
                    paused = False
                if event.key == pygame.K_h: debug_mode = not debug_mode
                
                # Tecla G para alternar Modo Dios en caliente
                if event.key == pygame.K_g:
                    GOD_MODE = not GOD_MODE
                    print(f"Invencibilidad: {GOD_MODE}")

        if not paused and not game_won:
            if is_dead:
                if pygame.time.get_ticks() - death_time > DEATH_DELAY:
                    reset_level(increment_attempt=True)
            else:
                if portal_cooldown > 0: portal_cooldown -= 1
                distance_traveled += current_game_speed
                attempt_text_x -= current_game_speed

                for p in players:
                    p.handle_input()
                    p.update(current_game_speed)
                for obj in objects: obj.update(current_game_speed)
                
                current_players = players[:] 
                for p in current_players:
                    collision = False
                    for obj in objects:
                        for tile in obj.tiles:
                            SPECIAL_IDS = [10, 11, 99, 25, 26, 27, 28] + list(SPEED_MAP.keys())
                            
                            if not p.rect.colliderect(tile['rect']) and tile['type'] not in SPECIAL_IDS: 
                                continue
                            
                            tid = tile['type']
                            tile_rect = tile['rect']

                            # Ganar
                            if tid == 99:
                                game_won = True
                                if music_loaded: pygame.mixer.music.stop()
                                break

                            # Portales
                            portal_hitbox = None
                            if tid in SPECIAL_IDS and tid != 99:
                                portal_hitbox = pygame.Rect(0, 0, 40, 90)
                                portal_hitbox.center = tile_rect.center

                            if (tid == 10 or tid == 11) and portal_cooldown == 0:
                                if p.rect.colliderect(portal_hitbox):
                                    if tid == 10 and len(players) == 1: 
                                        players.append(wave.Wave(p.rect.x, p.rect.y, current_game_speed, inverted=not p.current_gravity_inverted))
                                        portal_cooldown = 15 
                                    elif tid == 11: 
                                        p.set_gravity(False); p.set_mode(inverted=False) 
                                        players = [p]; portal_cooldown = 15; collision = False; break
                                continue

                            if tid in SPEED_MAP:
                                if p.rect.colliderect(portal_hitbox):
                                    current_game_speed = SPEED_MAP[tid]
                                    for wp in players: wp.set_speed(current_game_speed)
                                continue

                            if tid == 25 and p.rect.colliderect(portal_hitbox): p.set_gravity(True); continue
                            if tid == 26 and p.rect.colliderect(portal_hitbox): p.set_gravity(False); continue
                            if tid == 27 and p.rect.colliderect(portal_hitbox): p.set_mini(True); continue
                            if tid == 28 and p.rect.colliderect(portal_hitbox): p.set_mini(False); continue
                            if tid not in SPECIAL_IDS:
                                if not GOD_MODE: 
                                    if check_precise_collision(p.rect, tile_rect, tid):
                                        collision = True
                            
                            if collision: break
                        if collision: break
                    
                    if collision:
                        is_dead, death_time = True, pygame.time.get_ticks()
                        if music_loaded: pygame.mixer.music.stop()
                        break 
                    if game_won: break

        for obj in objects:
            for tile in obj.tiles:
                tid = tile['type']
                rect = tile['rect']
                if (tid == 9 or tid == 99) and not debug_mode: continue

                if tid in textures:
                    img = textures[tid]
                    draw_rect = img.get_rect(center=rect.center)
                    window.blit(img, draw_rect)
                else:
                    c = (255, 255, 255)
                    if tid >= 10: c = (100, 100, 255) 
                    pygame.draw.rect(window, c, rect)
                
                if debug_mode:
                    if tid == 7:
                        pygame.draw.line(window, (255, 0, 0), rect.bottomleft, rect.topright, 3)
                    elif tid == 8:
                        pygame.draw.line(window, (255, 0, 0), rect.topleft, rect.bottomright, 3)
                    elif tid == 17: 
                        end_p = (rect.left + 20, rect.top)
                        pygame.draw.line(window, (255, 0, 0), rect.bottomleft, end_p, 3)
                    elif tid == 18: 
                        end_p = (rect.left + 20, rect.bottom)
                        pygame.draw.line(window, (255, 0, 0), rect.topleft, end_p, 3)
                    elif tid in SPECIAL_IDS:
                        d = pygame.Rect(0,0,40,90); d.center = rect.center
                        pygame.draw.rect(window, (0,255,255), d, 2)
                    else:
                        pygame.draw.rect(window, (255, 0, 0), rect, 1)
        
        for p in players:
            p.draw(window)
            if debug_mode: 
                pygame.draw.circle(window, (0, 255, 0), p.rect.center, 3)
                pygame.draw.rect(window, (255, 255, 0), p.rect, 1)

        if GOD_MODE:
            txt_god = font_debug.render("Invencibilidad: Activada :)", True, (0, 255, 0))
            window.blit(txt_god, (10, HEIGHT - 30))

        if not game_won:
            if attempt_text_x > -200: 
                window.blit(font_attempts.render(f"Intento {attempts}", True, (255,255,255)), (attempt_text_x, HEIGHT//3))
            if map_total_width_px > 0:
                pct = min(1.0, distance_traveled / map_total_width_px)
                bar_w, bar_h = 500, 20
                bx, by = (WIDTH-bar_w)//2, 20
                pygame.draw.rect(window, (50,50,50), (bx, by, bar_w, bar_h))
                pygame.draw.rect(window, (0,255,0), (bx, by, int(bar_w*pct), bar_h))
                window.blit(font_progress.render(f"{int(pct*100)}%", True, (255,255,255)), (bx+bar_w+10, by-5))

        if paused and not is_dead and not game_won:
            window.blit(font_attempts.render("PAUSA", True, (255,255,255)), (WIDTH//2, HEIGHT//2))
            
        if game_won:
            window.blit(font_win.render("GANASTE", True, (255, 215, 0)), (WIDTH//2-200, HEIGHT//2))

        pygame.display.update()
    pygame.quit()

def start_game_thread():
    game_thread = threading.Thread(target=run_game)
    game_thread.start()

def mostrar_controles():
    frame_menu.pack_forget()
    frame_controles.pack(fill="both", expand=True)

def volver_al_menu():
    frame_controles.pack_forget()
    frame_menu.pack(fill="both", expand=True)

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

root = tk.Tk()
root.title("Wave Game")
root.attributes('-fullscreen', True) 
root.bind('<Escape>', lambda e: root.destroy())
BG_COLOR_VENTANA, COLOR_TEXTO = "#0984FF", "white"
BTN_FONT = ("Century Gothic", 14, "bold")
BTN_WIDTH, BTN_HEIGHT = 20, 2
BTN_BG, BTN_FG = "#ECF0F1", "#000000"
root.configure(bg=BG_COLOR_VENTANA)

frame_menu = tk.Frame(root, bg=BG_COLOR_VENTANA)
tk.Label(frame_menu, text="Wave Practice", font=("Century Gothic", 30, "bold"), bg=BG_COLOR_VENTANA, fg=COLOR_TEXTO).pack(pady=50)
tk.Button(frame_menu, text="JUGAR", command=start_game_thread, font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT, bg=BTN_BG, fg=BTN_FG).pack(pady=15)
tk.Button(frame_menu, text="CONTROLES", command=mostrar_controles, font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT, bg=BTN_BG, fg=BTN_FG).pack(pady=15)
tk.Button(frame_menu, text="SALIR", command=root.quit, font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT, bg=BTN_BG, fg=BTN_FG).pack(pady=15)

frame_controles = tk.Frame(root, bg=BG_COLOR_VENTANA)
tk.Label(frame_controles, text="Instrucciones", font=("Century Gothic", 24, "bold"), bg=BG_COLOR_VENTANA, fg=COLOR_TEXTO).pack(pady=40)
tk.Label(frame_controles, text="Manten presionado ESPACIO o ↑ (Flecha arriba) para subir.\nSuelta para bajar.\n'ESC' para Pausar.\n'Q' para Salir.\n'R' para Reiniciar.\n'H' para ver Hitboxes.\n'G' No lo presiones ;(.\n\n\n\n Pro Tip: Manten para subir, suelta para bajar, en partes rectas, oprime rapido :)", font=("Century Gothic", 14), bg=BG_COLOR_VENTANA, fg=COLOR_TEXTO).pack(pady=20)
tk.Button(frame_controles, text="VOLVER", command=volver_al_menu, font=BTN_FONT, width=BTN_WIDTH, height=BTN_HEIGHT, bg=BTN_BG, fg=BTN_FG).pack(pady=50)

frame_controles.pack_forget()
frame_menu.pack(fill="both", expand=True)

if __name__ == "__main__": root.mainloop()