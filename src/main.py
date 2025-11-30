import pygame
import math
import csv
import sys
import os
from collections import deque
from engine import Engine, EngineConfig

WIDTH, HEIGHT = 1280, 720
FPS = 60
LOG_CSV = "engine_timeseries.csv"
SOUND_FILE = os.environ.get("ENGINE_SOUND_FILE", None)

BG_COLOR = (10, 12, 16)
GAUGE_BG = (20, 22, 28)
ACCENT_CYAN = (0, 240, 255)
ACCENT_RED = (255, 40, 60)
ACCENT_ORANGE = (255, 160, 0)
TEXT_WHITE = (220, 220, 220)

def draw_text(screen, text, x, y, size=20, color=TEXT_WHITE, align="left"):
    font = pygame.font.SysFont("Consolas", size, bold=True)
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if align == "center": rect.center = (x, y)
    elif align == "right": rect.topright = (x, y)
    else: rect.topleft = (x, y)
    screen.blit(surf, rect)

class TelemetryGraph:
    def __init__(self, x, y, w, h, label, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.label = label
        self.data = deque(maxlen=100)
        self.max_val = 1.0

    def update(self, value):
        self.data.append(value)
        if value > self.max_val: self.max_val = value
        elif self.max_val > 1.0 and value < self.max_val * 0.9: self.max_val *= 0.99

    def draw(self, screen):
        pygame.draw.rect(screen, (15, 16, 20), self.rect)
        pygame.draw.rect(screen, (40, 44, 50), self.rect, 1)
        draw_text(screen, self.label, self.rect.x + 8, self.rect.y + 5, 14, self.color)
        draw_text(screen, f"{self.data[-1]:.0f}" if self.data else "0", self.rect.right - 8, self.rect.y + 5, 14, TEXT_WHITE, "right")

        if len(self.data) < 2: return

        points = []
        width_step = self.rect.w / (self.data.maxlen - 1)
        for i, val in enumerate(self.data):
            px = self.rect.x + (i * width_step)
            norm_y = (val / (self.max_val + 1e-6))
            py = self.rect.bottom - (norm_y * self.rect.h)
            points.append((px, py))

        if len(points) > 1:
            pygame.draw.lines(screen, self.color, False, points, 2)

class ModernGauge:
    def __init__(self, x, y, radius, label, max_val, units, color=ACCENT_CYAN):
        self.x, self.y, self.r = x, y, radius
        self.label, self.max_val, self.units = label, max_val, units
        self.color = color

    def draw(self, screen, value, is_redline=False):
        pygame.draw.circle(screen, GAUGE_BG, (self.x, self.y), self.r)
        pygame.draw.circle(screen, (30, 35, 40), (self.x, self.y), self.r - 5, 2)

        start_angle = 135
        sweep_range = 270
        
        for i in range(11):
            frac = i / 10.0
            angle_rad = math.radians(start_angle + (frac * sweep_range))
            ox = self.x + (self.r - 20) * math.cos(angle_rad)
            oy = self.y + (self.r - 20) * math.sin(angle_rad)
            ix = self.x + (self.r - 30) * math.cos(angle_rad)
            iy = self.y + (self.r - 30) * math.sin(angle_rad)
            tick_col = ACCENT_RED if (frac > 0.8 and "RPM" in self.label) else (80, 80, 80)
            pygame.draw.line(screen, tick_col, (ix, iy), (ox, oy), 3)

        val_frac = max(0.0, min(1.0, value / (self.max_val + 1e-9)))
        if val_frac > 0:
            steps = int(val_frac * 60)
            for i in range(steps):
                f1 = i / 60.0 * val_frac
                f2 = (i + 1) / 60.0 * val_frac
                a1 = math.radians(start_angle + f1 * sweep_range)
                a2 = math.radians(start_angle + f2 * sweep_range)
                ro, ri = self.r - 10, self.r - 18
                p1 = (self.x + ro * math.cos(a1), self.y + ro * math.sin(a1))
                p2 = (self.x + ro * math.cos(a2), self.y + ro * math.sin(a2))
                p3 = (self.x + ri * math.cos(a2), self.y + ri * math.sin(a2))
                p4 = (self.x + ri * math.cos(a1), self.y + ri * math.sin(a1))
                col = ACCENT_RED if is_redline or (val_frac > 0.9 and "RPM" in self.label) else self.color
                pygame.draw.polygon(screen, col, [p1, p2, p3, p4])

        current_angle = math.radians(start_angle + (val_frac * sweep_range))
        nx = self.x + (self.r - 25) * math.cos(current_angle)
        ny = self.y + (self.r - 25) * math.sin(current_angle)
        pygame.draw.line(screen, (255, 255, 255), (self.x, self.y), (nx, ny), 3)
        pygame.draw.circle(screen, (200, 200, 200), (self.x, self.y), 6)

        draw_text(screen, self.label, self.x, self.y + 40, 16, (120, 120, 120), "center")
        draw_text(screen, f"{value:.1f}", self.x, self.y - 10, 28, TEXT_WHITE, "center")
        draw_text(screen, self.units, self.x, self.y + 15, 14, self.color, "center")

class Slider:
    def __init__(self, x, y, w, label, min_v, max_v, step, value):
        self.rect = pygame.Rect(x, y, w, 24)
        self.label, self.min_v, self.max_v = label, min_v, max_v
        self.step, self.value = step, value
        self.dragging = False

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
            self.dragging = True
            self.set_from_mouse(ev.pos[0])
        elif ev.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif ev.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_mouse(ev.pos[0])

    def set_from_mouse(self, mx):
        val = self.min_v + ((mx - self.rect.x) / self.rect.w) * (self.max_v - self.min_v)
        self.value = max(self.min_v, min(self.max_v, val))
        if self.step > 0: self.value = round(self.value / self.step) * self.step

    def draw(self, screen):
        draw_text(screen, f"{self.label}", self.rect.x, self.rect.y - 20, 14, (150, 150, 150))
        draw_text(screen, f"{self.value:.2f}", self.rect.right - 40, self.rect.y - 20, 14, ACCENT_CYAN, "right")
        pygame.draw.rect(screen, (40, 44, 50), self.rect, border_radius=4)
        fill_w = int((self.value - self.min_v) / (self.max_v - self.min_v) * self.rect.w)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.h)
        pygame.draw.rect(screen, ACCENT_CYAN, fill_rect, border_radius=4)

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cargobrr Simulator")
    clock = pygame.time.Clock()

    cfg = EngineConfig()
    eng = Engine(cfg)

    s_throttle = Slider(50, 600, 250, "THROTTLE", 0.0, 1.0, 0.01, 0.0)
    s_load = Slider(350, 600, 250, "LOAD", 0.0, 1.0, 0.01, 0.0)
    s_redline = Slider(650, 600, 250, "REDLINE", 4000, 9000, 100, cfg.redline)
    sliders = [s_throttle, s_load, s_redline]

    g_rpm = ModernGauge(WIDTH//2, 300, 140, "RPM", cfg.redline, "x1000", ACCENT_CYAN)
    g_speed = ModernGauge(WIDTH//2 - 320, 320, 110, "SPEED", 240, "km/h", ACCENT_CYAN)
    g_boost = ModernGauge(WIDTH//2 + 320, 320, 110, "BOOST", 2.0, "bar", ACCENT_ORANGE)

    graph_rpm = TelemetryGraph(WIDTH - 320, HEIGHT - 120, 300, 100, "LIVE RPM", ACCENT_CYAN)

    csvf = open(LOG_CSV, "w", newline="")
    writer = csv.writer(csvf)
    writer.writerow(["t", "rpm", "throttle", "gear", "boost", "speed"])

    if SOUND_FILE and os.path.exists(SOUND_FILE):
        try: pygame.mixer.music.load(SOUND_FILE); pygame.mixer.music.play(-1)
        except: pass

    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: running = False
                if ev.key == pygame.K_e: eng.gear_up()
                if ev.key == pygame.K_q: eng.gear_down()
                if ev.key == pygame.K_r: eng = Engine(cfg)
                if ev.key == pygame.K_UP: s_throttle.value = min(1.0, s_throttle.value + 0.1)
                if ev.key == pygame.K_DOWN: s_throttle.value = max(0.0, s_throttle.value - 0.1)
            for s in sliders: s.handle_event(ev)

        keys = pygame.key.get_pressed()
        eng.set_brake(1.0 if keys[pygame.K_SPACE] else 0.0)
        eng.set_throttle(s_throttle.value)
        eng.set_load(s_load.value)
        eng.cfg.redline = s_redline.value

        eng.update(dt)
        st = eng.get_state()

        g_rpm.max_val = eng.cfg.redline
        graph_rpm.update(st['rpm'])

        screen.fill(BG_COLOR)
        
        pygame.draw.rect(screen, (15, 18, 22), (0, 0, WIDTH, 100))
        draw_text(screen, "CARGOBRR", 20, 20, 30, ACCENT_CYAN)
        
        status_col = ACCENT_RED if st['damaged'] else (100, 255, 100)
        draw_text(screen, f"TEMP: {st['coolant_temp']:.1f}C", WIDTH-250, 25, 20, status_col)
        draw_text(screen, f"AFR: {st['afr']:.1f}", WIDTH-450, 25, 20, TEXT_WHITE)
        draw_text(screen, f"GEAR: {st['gear'] if st['gear']>0 else 'N'}", WIDTH//2, 50, 40, ACCENT_ORANGE, "center")

        g_rpm.draw(screen, st['rpm'], is_redline=st['rpm']>eng.cfg.redline*0.95)
        g_speed.draw(screen, st['speed_kmh'])
        g_boost.draw(screen, st['boost'])
        graph_rpm.draw(screen)

        if st['backfire']:
            draw_text(screen, "💥", WIDTH//2 + 90, 450, 60, align="center")
        if st['limp_mode']:
            draw_text(screen, "CHECK ENGINE", WIDTH//2, 200, 25, ACCENT_RED, "center")
        if st['brake']:
             draw_text(screen, "BRAKE", WIDTH//2, 500, 25, ACCENT_RED, "center")

        for s in sliders: s.draw(screen)

        if SOUND_FILE and pygame.mixer.music.get_busy():
            vol = 0.2 + 0.8 * min(1.0, st["rpm"] / eng.cfg.redline)
            pygame.mixer.music.set_volume(min(1.0, vol))
            
        pygame.display.flip()
        
        writer.writerow([st['time'], st['rpm'], st['throttle'], st['gear'], st['boost'], st['speed_kmh']])

    csvf.close()
    pygame.quit()

if __name__ == "__main__":
    main()