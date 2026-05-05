# nabela-islam
AI Smart Traffic Control System – Adaptive City Simulation
Speciality: Instead of manually controlling lights…The system can automatically control traffic signals using logic (AI-like behavior). This project simulates an intelligent traffic control system where signals adapt dynamically based on real-time traffic density, with both manual and automated control modes.


FEATURES 

Nabela Islam
 1. Dual Mode System (Manual + Auto AI)
What happens:
Press key:
M → Manual mode
A → Auto mode
 Auto mode:
System decides which signal turns green

This feature introduces intelligent automation for traffic control.

 2. Adaptive Signal Timing (AI Logic)
What happens:
If more cars in one lane → longer green light
If no cars → skip that lane

Simple logic, but looks like AI

Example idea:

if cars_in_lane > 5:
    green_time = longer

 3. Real-Time Traffic Density System
 What happens:
Count number of cars in each lane
Show it on screen

Used by AI to make decisions


 4. Emergency Vehicle Priority System 
 What happens:
Ambulance appears
System automatically: Turns signals green for it 

5. Camera View Modes (Simulation Visualization Upgrade)
User can switch views:
Top View (Map style)
Driver View (from car perspective)
Intersection Close View
Controls:
C → change camera



Member 2 – Mohammad Abtahi Kafil Chy

1. Multi-direction Car Movement
 What it means:
Cars don’t come from only one side.
They can move:

Left → Right
Right → Left
Up → Down
Each car has a direction and speed.


2. Lane System
Road is divided into lanes (like real roads):
Lane 1 (left)
Lane 2 (middle)
Lane 3 (right)

Cars stay inside lanes.

Instead of free movement, cars follow fixed paths.
Prevents chaos and makes simulation structured

3. Smooth Movement & Turning
 
Cars don’t “jump” suddenly. They:
Move smoothly forward
Turn gradually at intersection

Instead of teleporting positions → gradual motion

4. Pedestrian Crossing System
Pedestrians randomly appear at zebra crossings
They request crossing using a virtual button
System:
Stops traffic temporarily
Allows safe crossing
Logic behavior:
Heavy traffic → delay crossing
Empty road → instant crossing

 5. Weather Impact System
Weather changes simulation behavior:
 Rain → cars move slower
 Fog → reduced visibility
 Clear → normal speed
AI adjusts signal timing based on weather conditions.





Member 3 – Ahnaf Al Muhsee

1. Score System (Traffic Efficiency Score)

You get points based on how well traffic flows:
No crash → +score
Smooth traffic → more score
Traffic jam → less score

Better management = higher score
Turns simulation into a “challenge game”

 2. Traffic Jam Detection

System checks:
Too many cars waiting in one lane = jam

If cars are stuck too long → system detects congestion

 3. Difficulty Scaling

As time passes:
More cars appear
Faster traffic
Harder to manage

 Keeps simulation challenging and not boring

4. Smart Traffic Violation Detection
Detects red-light violations
Cars crossing during red signal are flagged
Shows warning or penalty system
5. Traffic Prediction (Basic AI Forecast)
Predicts which lane will become congested next
Uses past traffic trends
Example logic:
if previous_density > current_density:
   predict_next_increase = True
