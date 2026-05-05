from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

W_WIDTH, W_HEIGHT = 1000, 800

# --- NABILA: GLOBAL MODES & AI ---
auto_mode = True
camera_mode = 0  # 0: Top View, 1: Driver View, 2: Intersection Close View
time_count = 0
tracked_car_id = None
cam_offset_x = 0
cam_offset_y = 0

# 0: N/S Green & E/W Red
# 1: E/W Green & N/S Red
lights_phase = 0 
light_timer = 300
base_green_time = 300

cars = []
lane_density = {'N': 0, 'S': 0, 'E': 0, 'W': 0}

ROAD_WIDTH = 100
STOP_LINE = 60 # Where cars wait for red lights

def spawn_car(is_ambulance=False):
    directions = ['N', 'S', 'E', 'W']
    d = random.choice(directions)
    
    # Simple coordinates based on direction
    if d == 'N': # Coming from North going South
        x, y = -25, 800
        dx, dy = 0, -1
    elif d == 'S': # Coming from South going North
        x, y = 25, -800
        dx, dy = 0, 1
    elif d == 'E': # Coming from East going West
        x, y = 800, 25
        dx, dy = -1, 0
    else: # Coming from West going East
        x, y = -800, -25
        dx, dy = 1, 0
        
    speed = 1.2 if not is_ambulance else 3.5 # Slower traffic to allow queues to build
    color = (1.0, 1.0, 1.0) if is_ambulance else (random.random(), random.random(), random.random())
    
    # Brake lights fix: if car is too dark, make it brighter
    color = (max(0.2, color[0]), max(0.2, color[1]), max(0.2, color[2]))
    
    cars.append({
        'dir': d,
        'x': x, 'y': y,
        'dx': dx, 'dy': dy,
        'speed': speed,
        'max_speed': speed,
        'is_ambulance': is_ambulance,
        'color': color,
        'waiting': False
    })

# --- CORE UPDATE LOGIC ---
def update_traffic_ai():
    global light_timer, lights_phase
    
    # Calculate density directly via coordinates
    lane_density['N'] = sum(1 for c in cars if c['dir'] == 'N' and c['y'] > 0 and c['waiting'])
    lane_density['S'] = sum(1 for c in cars if c['dir'] == 'S' and c['y'] < 0 and c['waiting'])
    lane_density['E'] = sum(1 for c in cars if c['dir'] == 'E' and c['x'] > 0 and c['waiting'])
    lane_density['W'] = sum(1 for c in cars if c['dir'] == 'W' and c['x'] < 0 and c['waiting'])

    if auto_mode:
        # Nabila Feature 4: Emergency Vehicle Priority
        ambulance_present = any(c['is_ambulance'] for c in cars)
        if ambulance_present:
            # Force light to Green for the ambulance's direction
            amb_dir = next(c['dir'] for c in cars if c['is_ambulance'])
            if amb_dir in ['N', 'S'] and lights_phase != 0:
                lights_phase = 0
                light_timer = 200
            elif amb_dir in ['E', 'W'] and lights_phase != 1:
                lights_phase = 1
                light_timer = 200
        else:
            light_timer -= 1
            if light_timer <= 0:
                lights_phase = 1 - lights_phase # Swap
                # Nabila Feature 2: Adaptive Signal Timing (AI Logic)
                # If the new phase has heavily congested lanes, give it longer!
                light_timer = base_green_time
                
                if lights_phase == 0: # N/S just turned green
                    if lane_density['N'] > 3 or lane_density['S'] > 3:
                        light_timer += 200 # Extended AI time
                    elif lane_density['N'] == 0 and lane_density['S'] == 0:
                        light_timer = 60 # Skip lane essentially
                else: # E/W just turned green
                    if lane_density['E'] > 3 or lane_density['W'] > 3:
                        light_timer += 200 
                    elif lane_density['E'] == 0 and lane_density['W'] == 0:
                        light_timer = 60 

def update_cars():
    global cars
    for i, c in enumerate(cars):
        c['waiting'] = False
        
        # Determine if facing a Red Light at the stop line
        facing_red = False
        if c['dir'] in ['N', 'S'] and lights_phase == 1: facing_red = True
        if c['dir'] in ['E', 'W'] and lights_phase == 0: facing_red = True
        
        # Only stop if we haven't crossed yet
        is_approaching = False
        if c['dir'] == 'N' and c['y'] > 0: is_approaching = True
        if c['dir'] == 'S' and c['y'] < 0: is_approaching = True
        if c['dir'] == 'E' and c['x'] > 0: is_approaching = True
        if c['dir'] == 'W' and c['x'] < 0: is_approaching = True

        dist_to_intersection = abs(c['y']) if c['dir'] in ['N', 'S'] else abs(c['x'])
        
        # Stop at intersection
        if facing_red and is_approaching and STOP_LINE < dist_to_intersection < STOP_LINE + 30:
            c['speed'] = 0
            c['waiting'] = True
        else:
            # Brake logic to avoid hitting car in front
            # Look ahead for cars in the same direction
            front_car_dist = 9999
            for other in cars:
                if other is c: continue
                if other['dir'] == c['dir']:
                    # Compute distance ahead
                    if c['dir'] == 'N' and other['y'] < c['y'] and other['y'] > c['y'] - 120:
                        front_car_dist = min(front_car_dist, c['y'] - other['y'])
                    elif c['dir'] == 'S' and other['y'] > c['y'] and other['y'] < c['y'] + 120:
                        front_car_dist = min(front_car_dist, other['y'] - c['y'])
                    elif c['dir'] == 'E' and other['x'] < c['x'] and other['x'] > c['x'] - 120:
                        front_car_dist = min(front_car_dist, c['x'] - other['x'])
                    elif c['dir'] == 'W' and other['x'] > c['x'] and other['x'] < c['x'] + 120:
                        front_car_dist = min(front_car_dist, other['x'] - c['x'])
            
            # Maintain gaps from cars
            if front_car_dist < 52: # Safe gap preventing modeling clipping
                c['speed'] = 0
                c['waiting'] = True
            else:
                # Regain speed safely
                c['speed'] += 0.1
                if c['speed'] > c['max_speed']: c['speed'] = c['max_speed']
        
        c['x'] += c['dx'] * c['speed']
        c['y'] += c['dy'] * c['speed']
        
    # Remove exited cars
    cars = [c for c in cars if -900 < c['x'] < 900 and -900 < c['y'] < 900]

# --- DRAWING ROUTINES ---
def draw_glued_car(car):
    glPushMatrix()
    glTranslatef(car['x'], car['y'], 10)
    
    # Align to direction
    if car['dir'] == 'N': glRotatef(180, 0, 0, 1) # N spawns facing -Y
    elif car['dir'] == 'S': glRotatef(0, 0, 0, 1) # S spawns facing +Y
    elif car['dir'] == 'E': glRotatef(90, 0, 0, 1) # E spawns facing -X
    elif car['dir'] == 'W': glRotatef(-90, 0, 0, 1) # W spawns facing +X
    
    # Chassis
    glColor3f(*car['color'])
    glScalef(2.0, 4.0, 1.2)
    glutSolidCube(10)
    
    # Roof/Windows
    glColor3f(0.1, 0.1, 0.1) # Dark windows
    glTranslatef(0, 0, 4)
    glScalef(0.8, 0.5, 1.0)
    glutSolidCube(10)
    
    if car['is_ambulance']:
        # Ambulance Siren
        pulse = abs(math.sin(time_count * 0.2))
        glColor3f(1.0, 0.0, 0.0) if pulse > 0.5 else glColor3f(0.0, 0.0, 1.0)
        glTranslatef(0, 0, 6)
        glutSolidCube(5)
        
    glPopMatrix()

def draw_environment():
    # Draw Roads
    glColor3f(0.15, 0.15, 0.15)
    glBegin(GL_QUADS)
    # Vertical Road (N/S)
    glVertex3f(-ROAD_WIDTH/2, 1000, 0); glVertex3f(ROAD_WIDTH/2, 1000, 0)
    glVertex3f(ROAD_WIDTH/2, -1000, 0); glVertex3f(-ROAD_WIDTH/2, -1000, 0)
    # Horizontal Road (E/W)
    glVertex3f(-1000, ROAD_WIDTH/2, 0); glVertex3f(1000, ROAD_WIDTH/2, 0)
    glVertex3f(1000, -ROAD_WIDTH/2, 0); glVertex3f(-1000, -ROAD_WIDTH/2, 0)
    glEnd()

    # Draw Traffic Lights
    def draw_signal(x, y, is_ns):
        glPushMatrix()
        glTranslatef(x, y, 30)
        
        # The pole
        glColor3f(0.2, 0.2, 0.2)
        glPushMatrix()
        glScalef(0.2, 0.2, 6.0)
        glutSolidCube(10)
        glPopMatrix()
        
        # The light
        glTranslatef(0, 0, 35)
        
        green_active = (lights_phase == 0 if is_ns else lights_phase == 1)
        if green_active:
            glColor3f(0.0, 1.0, 0.0) # Green
        else:
            glColor3f(1.0, 0.0, 0.0) # Red
            
        gluSphere(gluNewQuadric(), 8, 16, 16)
        glPopMatrix()

    # Place lights on 4 corners
    draw_signal(-ROAD_WIDTH/2 - 20, ROAD_WIDTH/2 + 20, is_ns=False) # West stopping incoming East
    draw_signal(ROAD_WIDTH/2 + 20, -ROAD_WIDTH/2 - 20, is_ns=False) # East stopping incoming West
    draw_signal(-ROAD_WIDTH/2 - 20, -ROAD_WIDTH/2 - 20, is_ns=True) # South stopping incoming North
    draw_signal(ROAD_WIDTH/2 + 20, ROAD_WIDTH/2 + 20, is_ns=True)   # North stopping incoming South

# Nabila Feature 3: Real-Time Traffic UI & Manual Controls
def draw_ui():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, W_WIDTH, 0, W_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    def render_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1,1,1)):
        glColor3f(*color)
        glRasterPos2f(x, y)
        for ch in text:
            glutBitmapCharacter(font, ord(ch))
            
    # Draw Dual Mode status
    mode_text = "AUTO (AI CONTROL)" if auto_mode else "MANUAL CONTROL"
    render_text(20, W_HEIGHT - 40, f"MODE: {mode_text}", color=(0.2, 1.0, 0.2) if auto_mode else (1.0, 0.5, 0.0))
    render_text(20, W_HEIGHT - 65, "Press 'A' for Auto, 'M' for Manual, 'C' for Camera", GLUT_BITMAP_HELVETICA_12)
    
    # Real-Time Density
    render_text(20, W_HEIGHT - 110, "REAL-TIME LANE DENSITY:", color=(0.8, 0.8, 1.0))
    render_text(20, W_HEIGHT - 135, f"North Queue: {lane_density['N']} Cars", GLUT_BITMAP_HELVETICA_12)
    render_text(20, W_HEIGHT - 155, f"South Queue: {lane_density['S']} Cars", GLUT_BITMAP_HELVETICA_12)
    render_text(20, W_HEIGHT - 175, f"East Queue: {lane_density['E']} Cars", GLUT_BITMAP_HELVETICA_12)
    render_text(20, W_HEIGHT - 195, f"West Queue: {lane_density['W']} Cars", GLUT_BITMAP_HELVETICA_12)

    if not auto_mode:
        # Draw explicit Manual Action buttons mapped structurally
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2f(30, 100); glVertex2f(230, 100); glVertex2f(230, 150); glVertex2f(30, 150)
        glVertex2f(250, 100); glVertex2f(450, 100); glVertex2f(450, 150); glVertex2f(250, 150)
        glEnd()
        
        tc_N = (0, 1, 0) if lights_phase == 0 else (1, 1, 1)
        tc_E = (0, 1, 0) if lights_phase == 1 else (1, 1, 1)
        
        render_text(45, 120, "FORCE N/S GREEN", color=tc_N)
        render_text(265, 120, "FORCE E/W GREEN", color=tc_E)
        render_text(30, 160, "[CLICK BUTTONS TO CHANGE LIGHTS]", font=GLUT_BITMAP_HELVETICA_12)

    if any(c['is_ambulance'] for c in cars):
        render_text(W_WIDTH//2 - 100, W_HEIGHT - 50, "EMERGENCY: CLEARING ROADS!", color=(1.0, 0.0, 0.0))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# --- APP SETUP ---
def idle():
    global time_count
    time_count += 1
    
    # Increased spawn rate so the HUD stats gather clear big numbers
    if random.random() < 0.035:
        spawn_car()
    if random.random() < 0.001:
        spawn_car(is_ambulance=True)
        
    update_traffic_ai()
    update_cars()
    
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Nabila Feature 5: Camera View Modes
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, W_WIDTH/W_HEIGHT, 0.1, 4500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == 0:
        # Map Style Top View - Now supports Arrow Key Panning
        gluLookAt(cam_offset_x, cam_offset_y, 1200, cam_offset_x, cam_offset_y, 0, 0, 1, 0)
    elif camera_mode == 1:
        # Driver Perspective (Chase Cam)
        global tracked_car_id
        tracked_car = None
        for c in cars:
            if id(c) == tracked_car_id:
                tracked_car = c
                break
                
        # Find a new car if current is invalid, or if it crosses the 750 bounds boundary
        if not tracked_car or abs(tracked_car['x']) > 750 or abs(tracked_car['y']) > 750:
            # Pick a car heavily approaching the intersection so we get a good view of the queue
            candidates = [c for c in cars if 300 < max(abs(c['x']), abs(c['y'])) < 750]
            if candidates:
                tracked_car = random.choice(candidates)
                tracked_car_id = id(tracked_car)
            elif cars:
                tracked_car = cars[0]
                tracked_car_id = id(tracked_car)
                
        if tracked_car:
            c = tracked_car
            # Position the camera slightly behind and above the roof
            gluLookAt(c['x'] - c['dx']*45, c['y'] - c['dy']*45, 35, 
                      c['x'] + c['dx']*200, c['y'] + c['dy']*200, 10, 
                      0, 0, 1)
        else:
            # Fallback when there are literally no cars on map
            gluLookAt(0, -500, 100, 0, 0, 0, 0, 0, 1)
    elif camera_mode == 2:
        # Intersection Close View - Supports Panning alongside the core
        gluLookAt(-350 + cam_offset_x, -350 + cam_offset_y, 480, cam_offset_x, cam_offset_y, 0, 0, 0, 1)

    draw_environment()
    for c in cars: draw_glued_car(c)
    draw_ui()

    glutSwapBuffers()

def keyboardListener(key, x, y):
    global auto_mode, camera_mode
    if key == b'a' or key == b'A':
        auto_mode = True
    elif key == b'm' or key == b'M':
        auto_mode = False
    elif key == b'c' or key == b'C':
        global cam_offset_x, cam_offset_y
        camera_mode = (camera_mode + 1) % 3
        cam_offset_x = 0
        cam_offset_y = 0
    glutPostRedisplay()

def specialKeyListener(key, x, y):
    global cam_offset_x, cam_offset_y
    if key == GLUT_KEY_UP:
        cam_offset_y += 35
    elif key == GLUT_KEY_DOWN:
        cam_offset_y -= 35
    elif key == GLUT_KEY_LEFT:
        cam_offset_x -= 35
    elif key == GLUT_KEY_RIGHT:
        cam_offset_x += 35
    glutPostRedisplay()

def mouseListener(button, state, x, y):
    global lights_phase
    # Map orthographic click since UI is top-left pinned mathematically
    # Y is inverted in GLUT (0 is top)
    real_y = W_HEIGHT - y
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not auto_mode:
        if 30 <= x <= 230 and 100 <= real_y <= 150:
            lights_phase = 0 # Force N/S
        elif 250 <= x <= 450 and 100 <= real_y <= 150:
            lights_phase = 1 # Force E/W
            
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(W_WIDTH, W_HEIGHT)
    glutInitWindowPosition(100, 10)
    glutCreateWindow(b"AI Smart Traffic Control System")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()
