#!/usr/bin/env python
from math import sqrt

of=open("../PrusaMendel/stl/calibration_export.gcode")
g=[i.replace("\n","").replace("\r","") for i in of]
of.close

def get_value(axis, parts):
    for i in parts:
        if (axis in i):
            return float(i[1:])
    return None


total_duration = 0
starting_velocity = 0
global_feedrate = 0
initial_feedrate = 0
X_last_position = 0
Y_last_position = 0
for i in g:
    if "G1" in i and ("X" in i or "Y" in i or "F" in i):
        parts = i.split(" ")
        X = get_value("X", parts[1:])
        Y = get_value("Y", parts[1:])
        F = get_value("F", parts[1:])

        if (X is None and Y is None and F is not None):
            global_feedrate = F
            continue
        
        feedrate = 0
        if (F is None):
            feedrate = global_feedrate
        else:
            feedrate = F

        distance = 0
        if (X is not None and Y is None):
            distance = X - X_last_position
            X_last_position = X
        elif (X is None and Y is not None):
            distance = Y - Y_last_position
            Y_last_position = Y
        elif (X is not None and Y is not None):
            X_distance = X - X_last_position
            Y_distance = Y - Y_last_position
            distance = sqrt(X_distance * X_distance + Y_distance * Y_distance)
            X_last_position = X
            Y_last_position = Y        

        time_for_move = distance / (feedrate / 60)
        acceleration = (feedrate - initial_feedrate) / time_for_move

        halfway_feedrate = initial_feedrate + acceleration * time_for_move / 2

        duration = 0
        if (halfway_feedrate == feedrate):
            time_full_feedrate = (feedrate - initial_feedrate) / acceleration
            distance_full_feedrate = (0.5 * (feedrate + initial_feedrate)) * time_full_feedrate
            duration = time_full_feedrate * 2 + (distance - distance_full_feedrate * 2) / feedrate
        else:
            duration = (halfway_feedrate * 2 - initial_feedrate) / acceleration

        total_duration += duration
    
    
print ("Total duration (in minutes): {0}".format(total_duration / 60))
