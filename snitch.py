import cv2
import numpy as np
import random
import time
import math
import mediapipe as mp

class GoldenSnitchGame:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.width = 1300
        self.height = 750
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        self.game_duration = 30
        self.catch_radius = 30
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.lives = 5
        self.level = 1
        self.game_started = False
        self.start_time = None
        
        self.snitches = []
        self.num_snitches = 1
        self.create_snitches()
        
        self.power_ups = []
        self.active_power_up = None
        self.power_up_timer = 0
        
        self.bludgers = []
        self.num_bludgers = 0
        
        self.particles = []
        self.hit_animations = []
        self.shake_intensity = 0
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.tracker_pos = None
        self.smoothed_pos = None
        self.smoothing_factor = 0.5
        
        self.difficulty = "EASY"
        
    def create_snitches(self):
        self.snitches = []
        for i in range(self.num_snitches):
            snitch = {
                'pos': [random.randint(100, self.width-100), 
                       random.randint(100, self.height-100)],
                'velocity': [random.choice([-8, -7, 7, 8]),
                            random.choice([-8, -7, 7, 8])],
                'radius': 25,
                'glow_phase': random.uniform(0, 2*math.pi)
            }
            self.snitches.append(snitch)
    
    def create_power_up(self):
        power_up_types = ['SLOW_TIME', 'DOUBLE_POINTS', 'SHIELD', 'MAGNET']
        power_up = {
            'pos': [random.randint(100, self.width-100), 
                   random.randint(100, self.height-100)],
            'type': random.choice(power_up_types),
            'radius': 25,
            'lifetime': 300
        }
        self.power_ups.append(power_up)
    
    def create_bludger(self):
        bludger = {
            'pos': [random.randint(100, self.width-100), 
                   random.randint(100, self.height-100)],
            'velocity': [random.choice([-6, -5, 5, 6]),
                        random.choice([-6, -5, 5, 6])],
            'radius': 25
        }
        self.bludgers.append(bludger)
    
    def create_particle_explosion(self, x, y, color, count=20):
        for _ in range(count):
            particle = {
                'pos': [x, y],
                'velocity': [random.uniform(-5, 5), random.uniform(-5, 5)],
                'color': color,
                'lifetime': random.randint(20, 40),
                'size': random.randint(2, 5)
            }
            self.particles.append(particle)
    
    def update_particles(self, frame):
        for particle in self.particles[:]:
            particle['pos'][0] += particle['velocity'][0]
            particle['pos'][1] += particle['velocity'][1]
            particle['velocity'][1] += 0.3
            particle['lifetime'] -= 1
            
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)
            else:
                alpha = particle['lifetime'] / 40.0
                cv2.circle(frame, 
                          (int(particle['pos'][0]), int(particle['pos'][1])), 
                          particle['size'], 
                          particle['color'], 
                          -1)
    
    def update_difficulty(self):
        if self.score >= 40 and self.difficulty != "INSANE":
            self.difficulty = "INSANE"
            self.num_snitches = 4
            self.num_bludgers = 3
            self.create_snitches()
            while len(self.bludgers) < 3:
                self.create_bludger()
        elif self.score >= 25 and self.difficulty == "MEDIUM":
            self.difficulty = "HARD"
            self.num_snitches = 3
            self.num_bludgers = 2
            self.create_snitches()
            while len(self.bludgers) < 2:
                self.create_bludger()
        elif self.score >= 12 and self.difficulty == "EASY":
            self.difficulty = "MEDIUM"
            self.num_snitches = 2
            self.num_bludgers = 1
            self.create_snitches()
            self.create_bludger()
    
    def update_snitch_position(self, snitch):
        speed_multiplier = 1.0
        if self.active_power_up == 'SLOW_TIME':
            speed_multiplier = 0.5
        
        snitch['pos'][0] += snitch['velocity'][0] * speed_multiplier
        snitch['pos'][1] += snitch['velocity'][1] * speed_multiplier
        
        if snitch['pos'][0] <= snitch['radius'] or snitch['pos'][0] >= self.width - snitch['radius']:
            snitch['velocity'][0] *= -1
            snitch['velocity'][0] += random.choice([-2, -1, 0, 1, 2])
            
        if snitch['pos'][1] <= snitch['radius'] or snitch['pos'][1] >= self.height - snitch['radius']:
            snitch['velocity'][1] *= -1
            snitch['velocity'][1] += random.choice([-2, -1, 0, 1, 2])
        
        max_speed = 10 + (self.level * 1.0)
        snitch['velocity'][0] = max(-max_speed, min(max_speed, snitch['velocity'][0]))
        snitch['velocity'][1] = max(-max_speed, min(max_speed, snitch['velocity'][1]))
        
        if random.random() < 0.04:
            snitch['velocity'][0] += random.choice([-3, -2, 2, 3])
            snitch['velocity'][1] += random.choice([-3, -2, 2, 3])
        
        snitch['glow_phase'] += 0.1
    
    def update_bludger_position(self, bludger):
        bludger['pos'][0] += bludger['velocity'][0]
        bludger['pos'][1] += bludger['velocity'][1]
        
        if bludger['pos'][0] <= bludger['radius'] or bludger['pos'][0] >= self.width - bludger['radius']:
            bludger['velocity'][0] *= -1
            
        if bludger['pos'][1] <= bludger['radius'] or bludger['pos'][1] >= self.height - bludger['radius']:
            bludger['velocity'][1] *= -1
    
    def detect_tracker(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            index_finger_tip = hand_landmarks.landmark[8]
            
            h, w, c = frame.shape
            cx = int(index_finger_tip.x * w)
            cy = int(index_finger_tip.y * h)
            
            if 0 <= cx < w and 0 <= cy < h:
                if self.smoothed_pos is None:
                    self.smoothed_pos = [cx, cy]
                else:
                    self.smoothed_pos[0] = int(self.smoothing_factor * cx + (1 - self.smoothing_factor) * self.smoothed_pos[0])
                    self.smoothed_pos[1] = int(self.smoothing_factor * cy + (1 - self.smoothing_factor) * self.smoothed_pos[1])
                
                self.tracker_pos = tuple(self.smoothed_pos)
                return True
        
        self.tracker_pos = None
        return False
    
    def check_catch(self, snitch):
        if self.tracker_pos is None:
            return False
        
        catch_radius = self.catch_radius
        if self.active_power_up == 'MAGNET':
            catch_radius = self.catch_radius * 2
        
        distance = np.sqrt((self.tracker_pos[0] - snitch['pos'][0])**2 + 
                          (self.tracker_pos[1] - snitch['pos'][1])**2)
        
        return distance < (catch_radius + snitch['radius'])
    
    def check_power_up_collision(self, power_up):
        if self.tracker_pos is None:
            return False
        
        distance = np.sqrt((self.tracker_pos[0] - power_up['pos'][0])**2 + 
                          (self.tracker_pos[1] - power_up['pos'][1])**2)
        
        return distance < (self.catch_radius + power_up['radius'])
    
    def check_bludger_hit(self, bludger):
        if self.tracker_pos is None or self.active_power_up == 'SHIELD':
            return False
        
        distance = np.sqrt((self.tracker_pos[0] - bludger['pos'][0])**2 + 
                          (self.tracker_pos[1] - bludger['pos'][1])**2)
        
        return distance < (30 + bludger['radius'])
    
    def reset_snitch(self, snitch):
        snitch['pos'] = [random.randint(100, self.width-100), 
                        random.randint(100, self.height-100)]
        snitch['velocity'] = [random.choice([-8, -7, 7, 8]),
                             random.choice([-8, -7, 7, 8])]
    
    def draw_snitch(self, frame, snitch):
        x, y = int(snitch['pos'][0]), int(snitch['pos'][1])
        
        glow_size = int(10 + 5 * math.sin(snitch['glow_phase']))
        cv2.circle(frame, (x, y), snitch['radius'] + glow_size, (0, 215, 255), 2)
        cv2.circle(frame, (x, y), snitch['radius'] + glow_size//2, (0, 200, 255), 1)
        
        cv2.circle(frame, (x, y), snitch['radius'], (0, 215, 255), -1)
        cv2.circle(frame, (x, y), snitch['radius'], (0, 165, 255), 3)
        
        wing_flap = int(5 * math.sin(snitch['glow_phase'] * 2))
        wing_points_left = np.array([
            [x - snitch['radius'], y],
            [x - snitch['radius'] - 20, y - 15 + wing_flap],
            [x - snitch['radius'] - 25, y],
            [x - snitch['radius'] - 20, y + 15 - wing_flap]
        ], np.int32)
        
        wing_points_right = np.array([
            [x + snitch['radius'], y],
            [x + snitch['radius'] + 20, y - 15 + wing_flap],
            [x + snitch['radius'] + 25, y],
            [x + snitch['radius'] + 20, y + 15 - wing_flap]
        ], np.int32)
        
        cv2.fillPoly(frame, [wing_points_left], (200, 200, 200))
        cv2.polylines(frame, [wing_points_left], True, (150, 150, 150), 2)
        cv2.fillPoly(frame, [wing_points_right], (200, 200, 200))
        cv2.polylines(frame, [wing_points_right], True, (150, 150, 150), 2)
    
    def draw_bludger(self, frame, bludger):
        x, y = int(bludger['pos'][0]), int(bludger['pos'][1])
        
        cv2.circle(frame, (x, y), bludger['radius'] + 5, (0, 0, 100), 2)
        cv2.circle(frame, (x, y), bludger['radius'], (0, 0, 50), -1)
        cv2.circle(frame, (x, y), bludger['radius'], (0, 0, 150), 3)
    
    def draw_power_up(self, frame, power_up):
        x, y = int(power_up['pos'][0]), int(power_up['pos'][1])
        
        colors = {
            'SLOW_TIME': (255, 200, 0),
            'DOUBLE_POINTS': (0, 255, 0),
            'SHIELD': (255, 0, 255),
            'MAGNET': (255, 255, 0)
        }
        
        symbols = {
            'SLOW_TIME': '⏱',
            'DOUBLE_POINTS': '2X',
            'SHIELD': '🛡',
            'MAGNET': '🧲'
        }
        
        color = colors.get(power_up['type'], (255, 255, 255))
        
        cv2.circle(frame, (x, y), power_up['radius'] + 5, color, 2)
        cv2.circle(frame, (x, y), power_up['radius'], color, -1)
        
        cv2.putText(frame, symbols.get(power_up['type'], '?'), 
                   (x - 15, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    def draw_ui(self, frame, time_left):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        title = f"GOLDEN SNITCH CHASE - {self.difficulty}"
        cv2.putText(frame, title, (self.width//2 - 300, 35), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 215, 255), 3)
        
        cv2.putText(frame, f"Score: {self.score}", (30, 70), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
        
        if self.combo > 1:
            combo_color = (0, 255, 0) if self.combo < 5 else (0, 255, 255)
            cv2.putText(frame, f"COMBO x{self.combo}!", (30, 100), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.8, combo_color, 2)
        
        for i in range(self.lives):
            cv2.circle(frame, (self.width - 50 - (i * 40), 70), 12, (0, 0, 255), -1)
        
        timer_color = (255, 255, 255) if time_left > 10 else (0, 0, 255)
        cv2.putText(frame, f"Time: {int(time_left)}s", (self.width//2 - 80, 70), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.7, timer_color, 2)
        
        if self.active_power_up:
            power_up_time_left = max(0, 10 - (time.time() - self.power_up_timer))
            cv2.putText(frame, f"POWER: {self.active_power_up} ({int(power_up_time_left)}s)", 
                       (self.width//2 - 150, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        if self.tracker_pos:
            tracker_color = (0, 255, 0)
            tracker_radius = 15
            
            if self.active_power_up == 'MAGNET':
                tracker_color = (255, 255, 0)
                tracker_radius = 30
            elif self.active_power_up == 'SHIELD':
                tracker_color = (255, 0, 255)
            
            cv2.circle(frame, self.tracker_pos, tracker_radius, tracker_color, 3)
            cv2.circle(frame, self.tracker_pos, tracker_radius + 5, tracker_color, 1)
            cv2.circle(frame, self.tracker_pos, self.catch_radius, tracker_color, 2)
            
            cv2.line(frame, (self.tracker_pos[0] - 10, self.tracker_pos[1]), 
                    (self.tracker_pos[0] + 10, self.tracker_pos[1]), tracker_color, 2)
            cv2.line(frame, (self.tracker_pos[0], self.tracker_pos[1] - 10), 
                    (self.tracker_pos[0], self.tracker_pos[1] + 10), tracker_color, 2)
            
            cv2.putText(frame, "FINGER", (self.tracker_pos[0] - 30, self.tracker_pos[1] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, tracker_color, 2)
    
    def show_start_screen(self, frame):
        overlay = frame.copy()
        
        for i in range(self.height):
            intensity = int(20 + (i / self.height) * 30)
            cv2.rectangle(overlay, (0, i), (self.width, i+1), (intensity, intensity - 5, intensity - 10), -1)
        
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
        
        border_thickness = 8
        cv2.rectangle(frame, (50, 50), (self.width-50, self.height-50), (0, 100, 150), border_thickness)
        cv2.rectangle(frame, (60, 60), (self.width-60, self.height-60), (0, 180, 255), 3)
        
        title_y = 150
        
        title = "THE GOLDEN SNITCH"
        title_x = self.width//2 - 450
        cv2.putText(frame, title, (title_x + 5, title_y + 5), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.8, (0, 0, 0), 8)
        cv2.putText(frame, title, (title_x, title_y), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.8, (0, 215, 255), 8)
        
        subtitle = "CHAMPIONSHIP CHALLENGE"
        sub_x = self.width//2 - 380
        cv2.putText(frame, subtitle, (sub_x, title_y + 70), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.5, (200, 200, 255), 4)
        
        cv2.line(frame, (self.width//2 - 400, title_y + 100), 
                (self.width//2 + 400, title_y + 100), (0, 200, 255), 3)
        
        box_y_start = 280
        box_height = 680
        
        content_overlay = frame.copy()
        cv2.rectangle(content_overlay, (150, box_y_start), 
                     (self.width-150, box_y_start + box_height), (10, 10, 30), -1)
        cv2.addWeighted(content_overlay, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (150, box_y_start), 
                     (self.width-150, box_y_start + box_height), (0, 180, 255), 4)
        
        left_col_x = 220
        right_col_x = self.width//2 + 80
        y_pos = box_y_start + 60
        
        cv2.putText(frame, "HOW TO PLAY", (left_col_x, y_pos), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.3, (255, 215, 0), 3)
        y_pos += 60
        
        instructions = [
            ("1.", "Point with your INDEX FINGER to control cursor"),
            ("2.", "Catch the flying Golden Snitches"),
            ("3.", "Build COMBOS for bonus points"),
            ("4.", "Collect glowing POWER-UPS"),
            ("5.", "AVOID dark Bludgers!")
        ]
        
        for num, text in instructions:
            cv2.putText(frame, num, (left_col_x, y_pos), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 255), 2)
            cv2.putText(frame, text, (left_col_x + 50, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            y_pos += 55
        
        y_pos = box_y_start + 60
        cv2.putText(frame, "POWER-UPS", (right_col_x, y_pos), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.3, (255, 215, 0), 3)
        y_pos += 60
        
        power_ups = [
            ("SLOW TIME", "Snitches move slower", (255, 200, 0)),
            ("2X POINTS", "Double your score!", (0, 255, 100)),
            ("SHIELD", "Bludger protection", (255, 0, 255)),
            ("MAGNET", "Larger catch area", (255, 255, 50))
        ]
        
        for name, desc, color in power_ups:
            cv2.circle(frame, (right_col_x + 20, y_pos - 10), 18, color, -1)
            cv2.circle(frame, (right_col_x + 20, y_pos - 10), 18, (255, 255, 255), 2)
            
            cv2.putText(frame, name, (right_col_x + 55, y_pos), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.85, color, 2)
            cv2.putText(frame, desc, (right_col_x + 55, y_pos + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            y_pos += 75
        
        y_pos = box_y_start + 480
        cv2.line(frame, (200, y_pos), (self.width-200, y_pos), (0, 150, 200), 2)
        y_pos += 50
        
        cv2.putText(frame, "DIFFICULTY PROGRESSION", (self.width//2 - 280, y_pos), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 215, 0), 3)
        y_pos += 55
        
        diff_levels = [
            ("EASY", "1 Snitch, 0 Bludgers", (100, 255, 100)),
            ("MEDIUM", "2 Snitches, 1 Bludger", (255, 200, 100)),
            ("HARD", "3 Snitches, 2 Bludgers", (255, 150, 50)),
            ("INSANE", "4 Snitches, 3 Bludgers!", (255, 50, 50))
        ]
        
        diff_x = 300
        for name, desc, color in diff_levels:
            cv2.putText(frame, name, (diff_x, y_pos), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 2)
            cv2.putText(frame, desc, (diff_x, y_pos + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            diff_x += 380
        
        y_pos = box_y_start + box_height - 80
        cv2.rectangle(frame, (self.width//2 - 350, y_pos - 20), 
                     (self.width//2 + 350, y_pos + 60), (0, 100, 180), -1)
        cv2.rectangle(frame, (self.width//2 - 350, y_pos - 20), 
                     (self.width//2 + 350, y_pos + 60), (0, 215, 255), 3)
        
        pulse = abs(math.sin(time.time() * 3))
        start_color = (int(100 + 155 * pulse), int(200 + 55 * pulse), 255)
        
        cv2.putText(frame, "Press SPACEBAR to Begin Your Quest!", 
                   (self.width//2 - 320, y_pos + 20), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.1, start_color, 3)
        
        cv2.putText(frame, "Press 'Q' to Quit", (self.width//2 - 120, y_pos + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        
        for _ in range(15):
            x = random.randint(100, self.width - 100)
            y = random.randint(80, 250)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            cv2.circle(frame, (x, y), size, (brightness, brightness, 255), -1)
    
    def show_end_screen(self, frame):
        overlay = frame.copy()
        for i in range(self.height):
            intensity = int(20 + (i / self.height) * 30)
            cv2.rectangle(overlay, (0, i), (self.width, i+1), (intensity, intensity - 5, intensity - 10), -1)
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)
        
        cv2.rectangle(frame, (200, 150), (self.width-200, self.height-150), (0, 215, 255), 3)
        
        cv2.putText(frame, "MISSION COMPLETE!", (self.width//2 - 350, 280), 
                   cv2.FONT_HERSHEY_DUPLEX, 2.2, (0, 215, 255), 4)
        
        y = 380
        cv2.putText(frame, f"FINAL SCORE: {self.score}", (self.width//2 - 250, y), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.8, (255, 255, 255), 4)
        
        y += 80
        cv2.putText(frame, f"Max Combo: x{self.max_combo}", (self.width//2 - 200, y), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 255), 3)
        
        y += 70
        cv2.putText(frame, f"Difficulty Reached: {self.difficulty}", (self.width//2 - 250, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
        
        y += 80
        if self.score >= 50:
            rating = "LEGENDARY SEEKER! 🏆"
        elif self.score >= 35:
            rating = "MASTER SEEKER! ⭐"
        elif self.score >= 20:
            rating = "EXCELLENT SEEKER! ✨"
        elif self.score >= 10:
            rating = "GOOD SEEKER!"
        else:
            rating = "KEEP PRACTICING!"
        
        cv2.putText(frame, rating, (self.width//2 - 180, y), 
                   cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 0), 2)
        
        y += 100
        pulse = abs(math.sin(time.time() * 3))
        button_color = (int(100 + 155 * pulse), int(200 + 55 * pulse), 255)
        
        cv2.putText(frame, "Press SPACEBAR to Play Again", 
                   (self.width//2 - 220, y), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.1, button_color, 3)
        
        cv2.putText(frame, "Press 'Q' to Quit", (self.width//2 - 120, y + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    
    def run(self):
        print("="*60)
        print("GOLDEN SNITCH CATCHING GAME - ENHANCED!")
        print("="*60)
        print("\nControls:")
        print("  SPACEBAR - Start/Restart")
        print("  Q - Quit")
        print("\nHow to Play:")
        print("  • Point with your INDEX FINGER")
        print("  • Move your finger to catch snitches")
        print("  • Works with any hand - left or right!")
        print("\nFeatures:")
        print("  • Multiple snitches")
        print("  • Power-ups & combos")
        print("  • Difficulty scaling")
        print("  • Bludger obstacles")
        print("="*60)
        
        game_state = "start"
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read from camera")
                break
            
            frame = cv2.flip(frame, 1)
            
            if game_state == "start":
                self.show_start_screen(frame)
                
            elif game_state == "playing":
                self.detect_tracker(frame)
                
                for snitch in self.snitches:
                    self.update_snitch_position(snitch)
                    
                    if self.check_catch(snitch):
                        points = 1
                        if self.active_power_up == 'DOUBLE_POINTS':
                            points *= 2
                        
                        self.score += points
                        self.combo += 1
                        self.max_combo = max(self.max_combo, self.combo)
                        
                        if self.combo > 2:
                            self.score += self.combo - 2
                        
                        self.reset_snitch(snitch)
                        self.create_particle_explosion(
                            int(snitch['pos'][0]), 
                            int(snitch['pos'][1]), 
                            (0, 255, 255), 
                            30
                        )
                        print(f"Caught! Score: {self.score} | Combo: x{self.combo}")
                
                for bludger in self.bludgers:
                    self.update_bludger_position(bludger)
                    
                    if self.check_bludger_hit(bludger):
                        self.lives -= 1
                        self.combo = 0
                        self.shake_intensity = 10
                        self.create_particle_explosion(
                            self.tracker_pos[0], 
                            self.tracker_pos[1], 
                            (0, 0, 255), 
                            40
                        )
                        print(f"Hit by Bludger! Lives: {self.lives}")
                        
                        if self.lives <= 0:
                            game_state = "end"
                            continue
                
                for power_up in self.power_ups[:]:
                    power_up['lifetime'] -= 1
                    
                    if power_up['lifetime'] <= 0:
                        self.power_ups.remove(power_up)
                    elif self.check_power_up_collision(power_up):
                        self.active_power_up = power_up['type']
                        self.power_up_timer = time.time()
                        self.power_ups.remove(power_up)
                        self.create_particle_explosion(
                            int(power_up['pos'][0]), 
                            int(power_up['pos'][1]), 
                            (255, 255, 0), 
                            25
                        )
                        print(f"Power-up collected: {self.active_power_up}")
                
                if self.active_power_up and (time.time() - self.power_up_timer) > 10:
                    self.active_power_up = None
                
                if random.random() < 0.003 and len(self.power_ups) < 2:
                    self.create_power_up()
                
                self.update_difficulty()
                
                for snitch in self.snitches:
                    self.draw_snitch(frame, snitch)
                
                for bludger in self.bludgers:
                    self.draw_bludger(frame, bludger)
                
                for power_up in self.power_ups:
                    self.draw_power_up(frame, power_up)
                
                self.update_particles(frame)
                
                elapsed = time.time() - self.start_time
                time_left = max(0, self.game_duration - elapsed)
                
                self.draw_ui(frame, time_left)
                
                if time_left <= 0:
                    game_state = "end"
                    print(f"\nTime's up! Final Score: {self.score}")
            
            elif game_state == "end":
                self.show_end_screen(frame)
            
            cv2.namedWindow('Golden Snitch Game', cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty('Golden Snitch Game', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.imshow('Golden Snitch Game', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\nThanks for playing!")
                break
            elif key == ord(' '):
                if game_state == "start" or game_state == "end":
                    self.score = 0
                    self.combo = 0
                    self.max_combo = 0
                    self.lives = 5
                    self.level = 1
                    self.difficulty = "EASY"
                    self.num_snitches = 1
                    self.num_bludgers = 0
                    self.snitches = []
                    self.bludgers = []
                    self.power_ups = []
                    self.particles = []
                    self.active_power_up = None
                    self.smoothed_pos = None
                    self.create_snitches()
                    self.start_time = time.time()
                    game_state = "playing"
                    print("\nGame started!")
        
        self.cap.release()
        self.hands.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = GoldenSnitchGame()
    game.run()