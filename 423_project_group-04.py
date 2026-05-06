from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import sys
import time

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 850

DIRECTIONS = ["EAST", "WEST", "NORTH", "SOUTH"]
DIR_LABELS = {
    "EAST": "Left -> Right",
    "WEST": "Right -> Left",
    "NORTH": "Down -> Up",
    "SOUTH": "Up -> Down",
}

SPAWN_POINTS = {
    "EAST": (-620.0, -40.0, 0.0),
    "WEST": (620.0, 40.0, 180.0),
    "NORTH": (40.0, -620.0, 90.0),
    "SOUTH": (-40.0, 620.0, -90.0),
}

LANE_OFFSETS = [-40.0, -10.0, 30.0]
LANE_NAMES = ["Lane 1", "Lane 2", "Lane 3 (Ambulance)"]
STOP_LINE = 128.0
ROAD_LIMIT = 680.0
INTERSECTION_HALF = 95.0
MIN_SPAWN_GAP = 135.0
MIN_FOLLOW_GAP = 82.0
QUEUE_GAP = 78.0

WEATHERS = ["CLEAR", "RAIN", "FOG"]
WEATHER_SPEED = {"CLEAR": 1.0, "RAIN": 0.65, "FOG": 0.78}
WEATHER_GREEN_BONUS = {"CLEAR": 0.0, "RAIN": 3.0, "FOG": 2.0}

cars = []
density_history = {direction: [] for direction in DIRECTIONS}
signals = {direction: "RED" for direction in DIRECTIONS}

mode = "AUTO"
active_green = "EAST"
green_timer = 0.0
green_duration = 6.0
spawn_timer = 0.0
simulation_time = 0.0
last_time = 0.0
score_timer = 0.0
density_timer = 0.0
score = 0
violations = 0
jam_warning = ""
prediction_text = "Prediction: collecting data"
weather = "CLEAR"
camera_index = 0
difficulty_level = 1
violators_remaining = 1
last_level = 1


def clamp(value, low, high):
    return max(low, min(high, value))


def weather_effect_text():
    if weather == "RAIN":
        return "Rain slows cars"
    if weather == "FOG":
        return "Fog reduces visibility"
    return "Clear weather gives normal speed"


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1.0, 1.0, 1.0)):
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def set_material(color):
    glColor3f(*color)


def draw_cube(x, y, z, sx, sy, sz, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    set_material(color)
    glutSolidCube(1.0)
    glPopMatrix()


def draw_cylinder(x, y, z, radius, height, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    set_material(color)
    quad = gluNewQuadric()
    gluCylinder(quad, radius, radius, height, 16, 2)
    glPopMatrix()


def draw_sphere(x, y, z, radius, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    set_material(color)
    quad = gluNewQuadric()
    gluSphere(quad, radius, 18, 18)
    glPopMatrix()


def reset_signals():
    for direction in DIRECTIONS:
        signals[direction] = "RED"
    signals[active_green] = "GREEN"


def create_car(direction=None, emergency=False, lane=None):
    if direction is None:
        direction = random.choice(DIRECTIONS)
    if lane is None:
        lane = random.randrange(3)
    sx, sy, angle = SPAWN_POINTS[direction]
    sx, sy = lane_center(direction, lane, sx, sy)
    return {
        "x": sx,
        "y": sy,
        "z": 9.0,
        "direction": direction,
        "lane": lane,
        "lane_name": LANE_NAMES[lane],
        "angle": angle,
        "speed": random.uniform(50.0, 78.0),
        "wait": 0.0,
        "emergency": emergency,
        "color": (1.0, 1.0, 1.0) if emergency else random.choice(
            [(0.1, 0.45, 1.0), (1.0, 0.18, 0.12), (0.95, 0.85, 0.15), (0.15, 0.8, 0.25), (0.9, 0.25, 0.85)]
        ),
        "violated": False,
        "will_violate": False,
        "turn": random.choice(["straight", "straight", "straight", "left", "right"]),
        "turned": False,
        "clearing_intersection": False,
    }


def lane_center(direction, lane, x, y):
    offset = LANE_OFFSETS[lane]
    if direction == "EAST":
        return x, -40.0 + offset * 1.0
    if direction == "WEST":
        return x, 40.0 - offset * 1.0
    if direction == "NORTH":
        return 40.0 - offset * 1.0, y
    return -40.0 + offset * 1.0, y


def lock_to_lane(car):
    car["x"], car["y"] = lane_center(car["direction"], car["lane"], car["x"], car["y"])


def reset_simulation():
    global cars, signals, mode, active_green, green_timer, green_duration
    global spawn_timer, simulation_time, last_time, score_timer, density_timer, score, violations
    global jam_warning, prediction_text, weather, camera_index
    global difficulty_level, violators_remaining, last_level
    cars = []
    signals = {direction: "RED" for direction in DIRECTIONS}
    mode = "AUTO"
    active_green = "EAST"
    green_timer = 0.0
    green_duration = 6.0
    spawn_timer = 0.0
    simulation_time = 0.0
    score_timer = 0.0
    density_timer = 0.0
    score = 100
    violations = 0
    jam_warning = ""
    prediction_text = "Prediction: collecting data"
    weather = "CLEAR"
    camera_index = 0
    difficulty_level = 1
    violators_remaining = 1
    last_level = 1
    last_time = time.perf_counter()
    for direction in DIRECTIONS:
        density_history[direction] = []
    for _ in range(7):
        add_car_with_gap()
    reset_signals()


def spawn_gap_clear(direction, lane):
    sx, sy, _ = SPAWN_POINTS[direction]
    sx, sy = lane_center(direction, lane, sx, sy)
    for car in cars:
        if car["direction"] == direction and car["lane"] == lane:
            if abs(car["x"] - sx) + abs(car["y"] - sy) < MIN_SPAWN_GAP:
                return False
    return True


def add_car_with_gap(emergency=False):
    global violators_remaining
    directions = DIRECTIONS[:]
    random.shuffle(directions)
    for direction in directions:
        lanes = [0, 1] if not emergency else [2]
        random.shuffle(lanes)
        for lane in lanes:
            if emergency or spawn_gap_clear(direction, lane):
                car = create_car(direction, emergency, lane)
                if not emergency and violators_remaining > 0:
                    car["will_violate"] = True
                    violators_remaining -= 1
                cars.append(car)
                return True
    return False


def density_counts():
    counts = {direction: 0 for direction in DIRECTIONS}
    for car in cars:
        if is_approaching_intersection(car):
            counts[car["direction"]] += 1
    return counts


def is_approaching_intersection(car):
    if car["direction"] == "EAST":
        return car["x"] < STOP_LINE
    if car["direction"] == "WEST":
        return car["x"] > -STOP_LINE
    if car["direction"] == "NORTH":
        return car["y"] < STOP_LINE
    return car["y"] > -STOP_LINE


def before_stop_line(car):
    if car["direction"] == "EAST":
        return car["x"] <= -STOP_LINE
    if car["direction"] == "WEST":
        return car["x"] >= STOP_LINE
    if car["direction"] == "NORTH":
        return car["y"] <= -STOP_LINE
    return car["y"] >= STOP_LINE


def signed_position(car):
    if car["direction"] == "EAST":
        return car["x"]
    if car["direction"] == "WEST":
        return -car["x"]
    if car["direction"] == "NORTH":
        return car["y"]
    return -car["y"]


def stop_line_position(direction):
    if direction in ("EAST", "NORTH"):
        return -STOP_LINE
    return -STOP_LINE


def red_light_queue_target(car):
    stop_target = stop_line_position(car["direction"])
    same_lane_ahead = []
    car_pos = signed_position(car)
    for other in cars:
        if other is car or other["direction"] != car["direction"] or other["lane"] != car["lane"]:
            continue
        other_pos = signed_position(other)
        if car_pos < other_pos <= stop_target + 20:
            same_lane_ahead.append(other_pos)
    if not same_lane_ahead:
        return stop_target
    same_lane_ahead.sort()
    return same_lane_ahead[0] - QUEUE_GAP


def reached_queue_target(car):
    return signed_position(car) >= red_light_queue_target(car)


def will_reach_queue_target(car, distance):
    if signals[car["direction"]] == "GREEN" or not before_stop_line(car):
        return False
    target = red_light_queue_target(car)
    current = signed_position(car)
    return current >= target or 0 <= target - current <= distance + 1.5


def near_stop_line(car):
    if car["direction"] == "EAST":
        return -STOP_LINE - 30 < car["x"] < -STOP_LINE + 10
    if car["direction"] == "WEST":
        return STOP_LINE - 10 < car["x"] < STOP_LINE + 30
    if car["direction"] == "NORTH":
        return -STOP_LINE - 30 < car["y"] < -STOP_LINE + 10
    return STOP_LINE - 10 < car["y"] < STOP_LINE + 30


def crossed_stop_line(car, old_pos):
    """Return True if the car moved from before to past the stop line this frame."""
    if car["direction"] == "EAST":
        return old_pos[0] <= -STOP_LINE and car["x"] > -STOP_LINE
    if car["direction"] == "WEST":
        return old_pos[0] >= STOP_LINE and car["x"] < STOP_LINE
    if car["direction"] == "NORTH":
        return old_pos[1] <= -STOP_LINE and car["y"] > -STOP_LINE
    return old_pos[1] >= STOP_LINE and car["y"] < STOP_LINE


def emergency_direction():
    for car in cars:
        if car["emergency"] and is_approaching_intersection(car):
            return car["direction"]
    return None


def choose_ai_signal():
    # Check for emergency vehicle priority first
    emergency = emergency_direction()
    if emergency:
        # Give immediate green light to ambulance direction
        duration = 8.0  # Extended green for ambulance
        return emergency, duration
    
    # Normal AI signal logic
    counts = density_counts()
    best_direction = active_green
    best_score = -1.0
    for direction in DIRECTIONS:
        if counts[direction] == 0:
            continue
        waiting = sum(car["wait"] for car in cars if car["direction"] == direction)
        long_waiting = sum(1 for car in cars if car["direction"] == direction and car["wait"] > 4.0)
        fairness_bonus = 1.5 if direction != active_green else 0.0
        lane_score = counts[direction] * 3.4 + waiting * 0.10 + long_waiting * 2.2 + fairness_bonus
        if lane_score > best_score:
            best_score = lane_score
            best_direction = direction
    if best_score < 0:
        best_direction = DIRECTIONS[(DIRECTIONS.index(active_green) + 1) % len(DIRECTIONS)]
    duration = clamp(4.0 + counts[best_direction] * 1.2 + WEATHER_GREEN_BONUS[weather], 4.0, 13.0)
    return best_direction, duration


def set_green(direction, duration=None):
    global active_green, green_timer, green_duration
    active_green = direction
    green_timer = 0.0
    if duration is not None:
        green_duration = duration
    reset_signals()


def update_ai_signals(dt):
    global green_timer
    green_timer += dt
    
    # Check for emergency vehicle priority every frame
    emergency = emergency_direction()
    if emergency and mode == "AUTO":
        # Immediate signal change for ambulance
        if active_green != emergency:
            set_green(emergency, 8.0)
        return
    
    # Normal signal timing
    if mode == "AUTO" and green_timer >= green_duration:
        direction, duration = choose_ai_signal()
        set_green(direction, duration)


def should_stop(car):
    if car["emergency"]:
        return False
    if car.get("clearing_intersection"):
        return False
    if signals[car["direction"]] != "GREEN" and before_stop_line(car) and reached_queue_target(car) and not car.get("will_violate"):
        return True
    for other in cars:
        if other is car or other["direction"] != car["direction"] or other["lane"] != car["lane"]:
            continue
        if distance_ahead(car, other) and abs(car["x"] - other["x"]) + abs(car["y"] - other["y"]) < MIN_FOLLOW_GAP:
            return True
    return False


def distance_ahead(car, other):
    if car["direction"] == "EAST":
        return other["x"] > car["x"] and abs(other["y"] - car["y"]) < 16
    if car["direction"] == "WEST":
        return other["x"] < car["x"] and abs(other["y"] - car["y"]) < 16
    if car["direction"] == "NORTH":
        return other["y"] > car["y"] and abs(other["x"] - car["x"]) < 16
    return other["y"] < car["y"] and abs(other["x"] - car["x"]) < 16


def move_car(car, dt):
    global score, violations
    speed = car["speed"] * WEATHER_SPEED[weather] * (1.0 + difficulty_level * 0.035)
    if car["emergency"]:
        speed *= 1.28
    distance = speed * dt
    old_pos = (car["x"], car["y"])
    if not car["emergency"] and not car.get("will_violate") and not car.get("clearing_intersection") and signals[car["direction"]] != "GREEN" and before_stop_line(car):
        target = red_light_queue_target(car)
        remaining = target - signed_position(car)
        if will_reach_queue_target(car, distance):
            place_car_at_signed_position(car, target)
            car["wait"] += dt
            return
    stopped = should_stop(car)
    if stopped:
        car["wait"] += dt
        return
    car["wait"] = max(0.0, car["wait"] - dt)
    if car["direction"] == "EAST":
        car["x"] += distance
    elif car["direction"] == "WEST":
        car["x"] -= distance
    elif car["direction"] == "NORTH":
        car["y"] += distance
    else:
        car["y"] -= distance
    if signals[car["direction"]] != "GREEN" and not car["violated"] and not car["emergency"]:
        if crossed_stop_line(car, old_pos):
            car["violated"] = True
            violations += 1
            score -= 8
    lock_to_lane(car)
    if car.get("clearing_intersection") and (abs(car["x"]) > STOP_LINE + 35 or abs(car["y"]) > STOP_LINE + 35):
        car["clearing_intersection"] = False
    if abs(car["x"]) < 72 and abs(car["y"]) < 72 and not car["turned"] and car["turn"] != "straight":
        apply_turn(car)


def place_car_at_signed_position(car, position):
    if car["direction"] == "EAST":
        car["x"] = position
    elif car["direction"] == "WEST":
        car["x"] = -position
    elif car["direction"] == "NORTH":
        car["y"] = position
    else:
        car["y"] = -position
    lock_to_lane(car)


def apply_turn(car):
    car["turned"] = True
    if car["turn"] == "left":
        mapping = {"EAST": "NORTH", "NORTH": "WEST", "WEST": "SOUTH", "SOUTH": "EAST"}
    else:
        mapping = {"EAST": "SOUTH", "SOUTH": "WEST", "WEST": "NORTH", "NORTH": "EAST"}
    car["direction"] = mapping[car["direction"]]
    car["angle"] = SPAWN_POINTS[car["direction"]][2]
    car["clearing_intersection"] = True
    lock_to_lane(car)


def remove_finished_cars():
    global cars, score
    kept = []
    for car in cars:
        outside = abs(car["x"]) > ROAD_LIMIT or abs(car["y"]) > ROAD_LIMIT
        if outside:
            score += 3 if not car["violated"] else 0
            if car["emergency"]:
                score += 15
        else:
            kept.append(car)
    cars = kept


def spawn_update(dt):
    global spawn_timer, difficulty_level, violators_remaining, last_level
    spawn_timer += dt
    difficulty_level = 1 + int(simulation_time // 35)
    if difficulty_level != last_level:
        violators_remaining = difficulty_level
        last_level = difficulty_level
    interval = clamp(2.1 - difficulty_level * 0.13, 0.65, 2.1)
    if spawn_timer >= interval:
        spawn_timer = 0.0
        if len(cars) < 42:
            add_car_with_gap()


def update_density_history():
    global jam_warning, prediction_text
    counts = density_counts()
    jams = []
    for direction in DIRECTIONS:
        density_history[direction].append(counts[direction])
        if len(density_history[direction]) > 24:
            density_history[direction].pop(0)
        long_wait = sum(1 for car in cars if car["direction"] == direction and car["wait"] > 5.0)
        if counts[direction] >= 7 or long_wait >= 4:
            jams.append(direction)
    if jams:
        jam_warning = "Jam: " + ", ".join(jams)
    else:
        jam_warning = "Jam: none"
    predicted = None
    predicted_value = -999
    for direction, history in density_history.items():
        if len(history) >= 6:
            trend = sum(history[-3:]) - sum(history[-6:-3])
            if trend > predicted_value:
                predicted_value = trend
                predicted = direction
    prediction_text = "Prediction: {} may get congested next".format(predicted) if predicted and predicted_value > 0 else "Prediction: stable traffic"


def update_efficiency_score():
    global score
    counts = density_counts()
    waiting_cars = sum(1 for car in cars if car["wait"] > 1.5)
    jammed_cars = sum(1 for car in cars if car["wait"] > 5.0)
    moving_cars = max(0, len(cars) - waiting_cars)
    total_cars = max(1, len(cars))
    moving_ratio = moving_cars / total_cars
    worst_density = max(counts.values()) if counts else 0
    severe_jam_limit = 5 + difficulty_level // 2
    heavy_density_limit = 9 + difficulty_level
    if moving_ratio >= 0.70 and moving_cars >= 3:
        score += 4
    elif moving_ratio >= 0.50:
        score += 2
    elif jammed_cars >= severe_jam_limit or worst_density >= heavy_density_limit:
        score -= 2
    else:
        score += 1


def update_simulation():
    global last_time, simulation_time, score_timer, density_timer, score
    now = time.perf_counter()
    dt = clamp(now - last_time, 0.0, 0.05)
    last_time = now
    simulation_time += dt
    score_timer += dt
    density_timer += dt
    update_ai_signals(dt)
    spawn_update(dt)
    for car in cars:
        move_car(car, dt)
    remove_finished_cars()
    if density_timer >= 1.0:
        density_timer = 0.0
        update_density_history()
    if score_timer >= 1.0:
        score_timer = 0.0
        update_efficiency_score()
    score = clamp(score, 0, 9999)
    glutPostRedisplay()


def idle():
    update_simulation()


def setup_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(62.0, WINDOW_WIDTH / float(WINDOW_HEIGHT), 1.0, 2500.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    if camera_index == 0:
        gluLookAt(0, -760, 620, 0, 0, 0, 0, 0, 1)
    elif camera_index == 1:
        gluLookAt(-70, -390, 95, 0, 80, 25, 0, 0, 1)
    else:
        gluLookAt(310, -360, 250, 0, 0, 0, 0, 0, 1)


def draw_ground():
    if weather in ["RAIN", "FOG"]:
        night_factor = 0.5  
    else:
        night_factor = (math.sin(simulation_time * 0.025) + 1.0) * 0.5
    
    
    if weather == "RAIN":
        sky_brightness = 0.25 + night_factor * 0.2  
        fog_color = (0.15 + sky_brightness * 0.3, 0.20 + sky_brightness * 0.3, 0.28 + sky_brightness * 0.4, 1.0)
        ground_base = (0.12, 0.32, 0.15)
        road_base = (0.35, 0.35, 0.32)  
    elif weather == "FOG":
        sky_brightness = 0.30 + night_factor * 0.25  
        fog_color = (0.62, 0.66, 0.68, 1.0)
        ground_base = (0.15, 0.35, 0.18)  
        road_base = (0.40, 0.40, 0.37)   
    else:  
        sky_brightness = 0.42 + night_factor * 0.35
        fog_color = (0.20 + sky_brightness * 0.45, 0.27 + sky_brightness * 0.45, 0.36 + sky_brightness * 0.55, 1.0)
        ground_base = (0.18, 0.42, 0.2)  
        road_base = (0.48, 0.48, 0.45)  
    
    glClearColor(*fog_color)
    
   
    draw_cube(0, 0, -2, 1400, 1400, 4, ground_base)

    draw_cube(0, 0, 0, 1420, 185, 3, road_base)
    draw_cube(0, 0, 0, 185, 1420, 3, road_base)
    
 
    if weather == "RAIN":
      
        draw_cube(0, 0, 1, 1400, 150, 1, (0.25, 0.25, 0.22))
        draw_cube(0, 0, 2, 150, 1400, 1, (0.25, 0.25, 0.22))
    else:
        draw_cube(0, 0, 0, 1400, 150, 2, (0.08, 0.08, 0.08))
        draw_cube(0, 0, 1, 150, 1400, 2, (0.08, 0.08, 0.08))
    
    
    if weather == "RAIN":
        draw_cube(0, 0, 2, 180, 180, 2, (0.08, 0.08, 0.08))  
    elif weather == "FOG":
        draw_cube(0, 0, 2, 180, 180, 2, (0.12, 0.12, 0.11))  
    else:
        draw_cube(0, 0, 2, 180, 180, 2, (0.1, 0.1, 0.1))  
    for pos in range(-560, 600, 90):
        if abs(pos) > 110:
            draw_cube(pos, 0, 4, 36, 4, 2, (1, 1, 0.15))
            draw_cube(0, pos, 4, 4, 36, 2, (1, 1, 0.15))
    if weather != "FOG":  
        for offset in [-64, 64]:
            draw_cube(0, offset, 5, 1400, 2, 2, (1, 1, 1))
            draw_cube(offset, 0, 5, 2, 1400, 2, (1, 1, 1))
    for i, offset in enumerate(LANE_OFFSETS):
        
        color = (0.25, 0.25, 0.25) if i < 2 else (0.8, 0.2, 0.2)
        draw_cube(0, -40.0 + offset, 6, 1400, 1.4, 2, color)
        draw_cube(0, 40.0 - offset, 6, 1400, 1.4, 2, color)
        draw_cube(40.0 - offset, 0, 6, 1.4, 1400, 2, color)
        draw_cube(-40.0 + offset, 0, 6, 1.4, 1400, 2, color)
    if weather != "FOG":  
        draw_cube(-128, -76, 6, 6, 145, 3, (1.0, 1.0, 1.0))
        draw_cube(128, 76, 6, 6, 145, 3, (1.0, 1.0, 1.0))
        draw_cube(76, -128, 6, 145, 6, 3, (1.0, 1.0, 1.0))
        draw_cube(-76, 128, 6, 145, 6, 3, (1.0, 1.0, 1.0))
    if weather != "FOG":  
        for pos in [-470, -250, 250, 470]:
            draw_cube(pos, -70, 6, 24, 8, 2, (1.0, 1.0, 1.0))
            draw_cube(pos + 14, -70, 6, 8, 18, 2, (1.0, 1.0, 1.0))
            draw_cube(pos, 70, 6, 24, 8, 2, (1.0, 1.0, 1.0))
            draw_cube(pos - 14, 70, 6, 8, 18, 2, (1.0, 1.0, 1.0))
            draw_cube(-70, pos, 6, 8, 24, 2, (1.0, 1.0, 1.0))
            draw_cube(-70, pos + 14, 6, 18, 8, 2, (1.0, 1.0, 1.0))
            draw_cube(70, pos, 6, 8, 24, 2, (1.0, 1.0, 1.0))
            draw_cube(70, pos - 14, 6, 18, 8, 2, (1.0, 1.0, 1.0))


def draw_buildings():
    locations = [(-360, -330), (-520, 260), (350, 310), (520, -260), (-270, 420), (290, -430), (-610, -500), (610, 500)]
    for index, (x, y) in enumerate(locations):
        height = 90 + (index % 3) * 45
        width = 80 + (index % 2) * 25
        depth = 80 + (index % 4) * 12
        
        if weather == "RAIN":
            base_color = (0.22 + index * 0.02, 0.25, 0.31)  
            roof_color = (0.65, 0.72, 0.78)  
        elif weather == "FOG":
            base_color = (0.25 + index * 0.02, 0.28, 0.34) 
            roof_color = (0.70, 0.75, 0.80) 
        else:  
            base_color = (0.28 + index * 0.025, 0.31, 0.39) 
            roof_color = (0.75, 0.85, 1.0) 
        
        draw_cube(x, y, height / 2, width, depth, height, base_color)
        draw_cube(x, y - depth / 2 - 2, height + 8, width + 5, 5, 16, roof_color)
        
    
        for row in range(3, int(height), 28):
            for col in [-0.25, 0.25]:
                lit = (index + row) % 3 != 0
                if weather == "RAIN":
                    window_color = (0.8, 0.7, 0.25) if lit else (0.06, 0.08, 0.12)  
                elif weather == "FOG":
                    window_color = (0.6, 0.5, 0.2) if lit else (0.05, 0.07, 0.10)  
                else:
                    window_color = (1.0, 0.86, 0.35) if lit else (0.08, 0.1, 0.14) 
                draw_cube(x + col * width, y - depth / 2 - 4, row, 12, 3, 10, window_color)


def draw_tree(x, y):
    draw_cube(x, y, 18, 10, 10, 36, (0.38, 0.20, 0.08))
    draw_sphere(x, y, 48, 25, (0.05, 0.38, 0.12))
    draw_sphere(x - 12, y + 6, 40, 18, (0.07, 0.45, 0.15))
    draw_sphere(x + 12, y - 8, 42, 18, (0.04, 0.32, 0.10))


def draw_street_lamp(x, y):
    draw_cube(x, y, 38, 6, 6, 76, (0.08, 0.08, 0.08))
    draw_cube(x + 16, y, 76, 32, 5, 5, (0.08, 0.08, 0.08))
    if weather == "FOG":
        draw_sphere(x + 32, y, 72, 8, (0.3, 0.26, 0.1))  
    else:
        draw_sphere(x + 32, y, 72, 8, (1.0, 0.88, 0.35))


def draw_city_details():
    for x in [-560, -390, -220, 220, 390, 560]:
        draw_tree(x, -125)
        draw_tree(x, 125)
    for y in [-560, -390, -220, 220, 390, 560]:
        draw_tree(-125, y)
        draw_tree(125, y)
    for x, y in [(-185, -185), (185, -185), (-185, 185), (185, 185), (-520, -105), (520, 105), (-105, 520), (105, -520)]:
        draw_street_lamp(x, y)
    draw_cube(-185, -185, 18, 50, 18, 36, (0.10, 0.16, 0.22))
    draw_cube(185, 185, 18, 50, 18, 36, (0.10, 0.16, 0.22))
    draw_cube(-185, -185, 40, 46, 4, 10, (0.05, 0.25, 0.9))
    draw_cube(185, 185, 40, 46, 4, 10, (0.9, 0.18, 0.05))


def draw_traffic_light(direction, x, y, angle=0.0):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle, 0, 0, 1)
    draw_cube(0, 0, 4, 34, 34, 8, (0.02, 0.02, 0.02))
    draw_cube(0, 0, 55, 12, 12, 110, (0.03, 0.03, 0.03))
    draw_cube(0, 0, 122, 42, 24, 64, (0.01, 0.01, 0.01))
    state = signals[direction]
    if weather == "FOG":
        red = (0.3, 0.01, 0.01) if state == "RED" else (0.05, 0.0, 0.0)
        yellow = (0.3, 0.25, 0.01) if state == "YELLOW" else (0.05, 0.04, 0.0)
        green = (0.0, 0.3, 0.03) if state == "GREEN" else (0.0, 0.05, 0.0)
    else:
        red = (1.0, 0.05, 0.03) if state == "RED" else (0.18, 0.0, 0.0)
        yellow = (1.0, 0.85, 0.05) if state == "YELLOW" else (0.18, 0.14, 0.0)
        green = (0.0, 1.0, 0.1) if state == "GREEN" else (0.0, 0.16, 0.0)
    draw_sphere(0, -13, 140, 9, red)
    draw_sphere(0, -13, 122, 9, yellow)
    draw_sphere(0, -13, 104, 9, green)
    if state == "RED" and weather != "FOG":
        draw_sphere(0, -15, 140, 14, (0.45, 0.02, 0.02))
    elif state == "GREEN" and weather != "FOG":
        draw_sphere(0, -15, 104, 14, (0.02, 0.45, 0.04))
    draw_cube(0, -17, 104, 32, 3, 58, (0.0, 0.0, 0.0))
    glPopMatrix()


def draw_overhead_signal(direction, x, y, angle):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle, 0, 0, 1)
    draw_cube(0, 0, 70, 10, 10, 140, (0.03, 0.03, 0.03))
    draw_cube(45, 0, 136, 90, 8, 8, (0.03, 0.03, 0.03))
    draw_traffic_light(direction, 86, 0, 90)
    glPopMatrix()


def draw_all_lights():
    draw_traffic_light("EAST", -155, -112, 0)
    draw_traffic_light("WEST", 155, 112, 180)
    draw_traffic_light("NORTH", 112, -155, 90)
    draw_traffic_light("SOUTH", -112, 155, -90)
    draw_traffic_light("EAST", -155, 112, 0)
    draw_traffic_light("WEST", 155, -112, 180)
    draw_traffic_light("NORTH", -112, -155, 90)
    draw_traffic_light("SOUTH", 112, 155, -90)
    draw_overhead_signal("EAST", -210, -72, 0)
    draw_overhead_signal("WEST", 210, 72, 180)
    draw_overhead_signal("NORTH", 72, -210, 90)
    draw_overhead_signal("SOUTH", -72, 210, -90)


def draw_car(car):
    glPushMatrix()
    glTranslatef(car["x"], car["y"], car["z"])
    glRotatef(car["angle"], 0, 0, 1)
    
    if car["emergency"]:
        body = (1.0, 1.0, 1.0)
    else:
        if weather == "RAIN":
            r, g, b = car["color"]
            body = (r * 0.7, g * 0.7, b * 0.7)  
        elif weather == "FOG":
            r, g, b = car["color"]
            body = (r * 0.8, g * 0.8, b * 0.8)  
        else:
            body = car["color"] 
    
    draw_cube(0, 0, 8, 42, 24, 16, body)
    
    if weather == "RAIN":
        draw_cube(2, 0, 22, 24, 18, 12, (0.08, 0.12, 0.18)) 
        draw_cube(0, 0, 1, 40, 22, 1, (0.15, 0.15, 0.12))
    elif weather == "FOG":
        draw_cube(2, 0, 22, 24, 18, 12, (0.10, 0.14, 0.20))  
    else:
        draw_cube(2, 0, 22, 24, 18, 12, (0.12, 0.18, 0.25))  
    
 
    draw_cube(-17, -13, 2, 8, 5, 5, (0.02, 0.02, 0.02))
    draw_cube(17, -13, 2, 8, 5, 5, (0.02, 0.02, 0.02))
    draw_cube(-17, 13, 2, 8, 5, 5, (0.02, 0.02, 0.02))
    draw_cube(17, 13, 2, 8, 5, 5, (0.02, 0.02, 0.02))
    
    if car["emergency"]:
        draw_cube(0, 0, 32, 20, 7, 6, (1, 0, 0))
        draw_cube(0, -13, 15, 5, 3, 10, (1, 0, 0))
    if car["violated"] and weather not in ["RAIN", "FOG"]:
        draw_cube(0, 0, 42, 12, 12, 4, (1, 0, 0))
    glPopMatrix()



def draw_weather_effects():
    if weather == "RAIN":
        glColor3f(0.45, 0.65, 1.0)
        glLineWidth(2)
        glBegin(GL_LINES)
        for _ in range(1200):
            x = random.uniform(-1200, 1200)
            y = random.uniform(-1200, 1200)
            z = random.uniform(20, 800)
            glVertex3f(x, y, z)
            wind_offset = random.uniform(-8, 12)
            glVertex3f(x + 20 + wind_offset, y - 18, z - 80)
        glEnd()
        glLineWidth(1)
        glPointSize(1)
        
    elif weather == "FOG":
        fog_layer_defs = [
            (50, (0.85, 0.87, 0.89)),
            (100, (0.82, 0.84, 0.86)),
            (150, (0.79, 0.81, 0.83)),
            (200, (0.76, 0.78, 0.80)),
            (250, (0.73, 0.75, 0.77)),
            (300, (0.70, 0.72, 0.74)),
            (350, (0.67, 0.69, 0.71)),
            (400, (0.64, 0.66, 0.68)),
            (450, (0.61, 0.63, 0.65))
        ]
        
        for z, color in fog_layer_defs:
            glColor3f(*color)
            glLineWidth(1)
            glBegin(GL_LINES)
            step = 30 
            for pos in range(-1400, 1401, step):
                glVertex3f(pos, -1400, z)
                glVertex3f(pos, 1400, z)
                glVertex3f(-1400, pos, z)
                glVertex3f(1400, pos, z)
            glEnd()
        
    
        glColor3f(0.80, 0.82, 0.84)
        glLineWidth(1)
        glBegin(GL_LINES)
        for _ in range(400):
            y = random.uniform(-1200, 1200)
            z = random.uniform(30, 450)
            offset = math.sin(simulation_time * 0.5 + y * 0.01) * 15
            glVertex3f(-1200, y, z)
            glVertex3f(1200, y + random.uniform(-40, 40) + offset, z + random.uniform(-15, 15))
        glEnd()
        
      
        glColor3f(0.72, 0.74, 0.76)
        for _ in range(8):
            x = random.uniform(-700, 700)
            y = random.uniform(-700, 700)
            size = random.uniform(80, 120)
            draw_cube(x, y, 6, size, size, 15, (0.72, 0.74, 0.76))


def draw_hud():
    counts = density_counts()
    y = WINDOW_HEIGHT - 28
    draw_text(18, y, "AI Smart Traffic Control System - Adaptive City Simulation", color=(0.2, 1.0, 0.5))
    y -= 28
    draw_text(18, y, "Mode: {} | Green: {} | Timer: {:.1f}/{:.1f} | Weather: {} | Camera: {}".format(mode, active_green, green_timer, green_duration, weather, camera_index + 1))
    y -= 24
    draw_text(18, y, "Weather Effect: {} | AI green bonus: +{:.1f}s".format(weather_effect_text(), WEATHER_GREEN_BONUS[weather]))
    y -= 24
    draw_text(18, y, "Density EAST:{} WEST:{} NORTH:{} SOUTH:{} | Cars:{} | Difficulty:{}".format(counts["EAST"], counts["WEST"], counts["NORTH"], counts["SOUTH"], len(cars), difficulty_level))
    y -= 24
    emergency = emergency_direction()
    if emergency:
        emergency_text = "AMBULANCE PRIORITY: {} road GREEN - All other directions RED".format(emergency)
    else:
        emergency_text = "Ambulance active: none"
    draw_text(18, y, "Score: {} | Violations: {} | {} | {} | {}".format(score, violations, jam_warning, emergency_text, prediction_text), color=(1.0, 0.9, 0.3))
    y -= 24
    draw_text(18, y, "Controls: A Auto, M Manual, 1-4 Green, C Camera, W Weather, E Ambulance, R Reset, ESC Exit")
    if mode == "AUTO":
        draw_text(18, 110, "Auto mode Is On", font=GLUT_BITMAP_HELVETICA_18, color=(0.1, 1.0, 0.2))


def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    setup_camera()
    

    draw_ground()
    draw_buildings()
    draw_city_details()
    draw_all_lights()
    for car in cars:
        draw_car(car)
    
    draw_weather_effects()
    draw_hud()
    glutSwapBuffers()


def keyboard(key, x, y):
    global mode, camera_index, weather
    normalized = key.decode("utf-8").lower() if isinstance(key, bytes) else str(key).lower()
    if normalized == "\x1b":
        glutLeaveMainLoop()
        return
    if normalized == "a":
        mode = "AUTO"
    elif normalized == "m":
        mode = "MANUAL"
    elif normalized in ("1", "2", "3", "4"):
        mode = "MANUAL"
        set_green(DIRECTIONS[int(normalized) - 1], 9999.0)
    elif normalized == "c":
        camera_index = (camera_index + 1) % 3
    elif normalized == "w":
        weather = WEATHERS[(WEATHERS.index(weather) + 1) % len(WEATHERS)]
    elif normalized == "e":
        add_car_with_gap(True)
    elif normalized == "r":
        reset_simulation()
    glutPostRedisplay()


def init_gl():
    glEnable(GL_DEPTH_TEST)


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(40, 20)
    glutCreateWindow(b"AI Smart Traffic Control System - 3D Adaptive City Simulation")
    init_gl()
    reset_simulation()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutIdleFunc(idle)
    glutMainLoop()


if __name__ == "__main__":
    main()
