import math
import numpy as np
import json
import time
import random

class EngineConfig:
    def __init__(self):
        self.idle_rpm = 900.0
        self.redline = 7500.0
        self.inertia = 0.02
        self.final_drive = 3.9
        self.gear_ratios = [0.0, 3.8, 2.3, 1.5, 1.1, 0.9] 
        self.max_boost_bar = 1.6
        self.vehicle_mass = 1350.0
        self.wheel_radius = 0.33
        self.drag_coefficient = 0.30
        self.frontal_area = 2.2
        self.air_density = 1.225
        self.turbo_inertia = 0.2  # Lower = faster spool
        self.wastegate_open_at = 1.0
        self.cooling_efficiency = 0.6
        self.ambient_temp = 25.0
        self.max_coolant_temp = 120.0
        self.overheat_rate = 0.08

class EngineState:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rpm = cfg.idle_rpm
        self.throttle = 0.0
        self.load = 0.0
        self.current_gear = 1
        self.boost = 0.0
        self.target_boost = 0.0
        self.coolant_temp = cfg.ambient_temp
        self.limp_mode = False
        self.damaged = False
        self.speed = 0.0
        self._start_time = time.time()
        self.fuel_cut = False
        self.backfire = False
        self.brake_pedal = 0.0

    def time(self):
        return time.time() - self._start_time

class Engine:
    def __init__(self, cfg=None):
        self.cfg = cfg or EngineConfig()
        self.state = EngineState(self.cfg)
        self.torque_map = np.array([
            [800, 160], [1500, 200], [2500, 280],
            [3500, 320], [4500, 340], [5500, 330],
            [6500, 300], [7500, 240], [8000, 100]
        ], dtype=float)
        self.last_throttle = 0.0

    def torque_at_rpm(self, rpm):
        rpms = self.torque_map[:,0]
        torques = self.torque_map[:,1]
        return float(np.interp(max(rpms[0], rpm), rpms, torques))

    def afr_estimate(self, rpm, throttle):
        base = 14.7 - (3.5 * throttle)
        if self.state.boost > 0.1: base -= (self.state.boost * 1.2)
        if self.state.fuel_cut: base = 22.0
        return max(10.0, min(22.0, base))

    def update_turbo(self, dt):
        s = self.state
        rpm_frac = s.rpm / self.cfg.redline
        flow_factor = min(1.0, rpm_frac * 1.5)
        
        s.target_boost = s.throttle * self.cfg.max_boost_bar * flow_factor
        
        # Spool up or down 
        if s.target_boost > s.boost:
            rate = 2.0 * (1.0 + rpm_frac) # Spools faster at high RPM
            s.boost += (s.target_boost - s.boost) * dt * rate
        else:
            s.boost += (s.target_boost - s.boost) * dt * 3.0

    def update_vehicle(self, engine_torque, dt):
        s = self.state
        gear_ratio = self.cfg.gear_ratios[s.current_gear]
        
        if s.current_gear == 0:
            wheel_force = 0.0
        else:
            wheel_tau = engine_torque * gear_ratio * self.cfg.final_drive
            wheel_force = wheel_tau / self.cfg.wheel_radius

        aero = 0.5 * self.cfg.air_density * self.cfg.drag_coefficient * self.cfg.frontal_area * (s.speed**2)
        roll = 9.81 * 0.015 * self.cfg.vehicle_mass
        slope = s.load * 2000.0
        brake = s.brake_pedal * 10000.0 

        net_force = wheel_force - (aero + roll + slope + brake)
        accel = net_force / self.cfg.vehicle_mass
        s.speed = max(0.0, s.speed + accel * dt)

        # Clutch
        if s.current_gear > 0:
            wheel_rpm = (s.speed / (2 * math.pi * self.cfg.wheel_radius)) * 60.0
            target_rpm = wheel_rpm * gear_ratio * self.cfg.final_drive
            s.rpm = (s.rpm * 0.6) + (target_rpm * 0.4)

    def update(self, dt):
        s = self.state

        # Rev Limit
        if s.rpm > self.cfg.redline + 50: s.fuel_cut = True
        elif s.fuel_cut and s.rpm < self.cfg.redline - 150: s.fuel_cut = False
        s.backfire = False
        if s.rpm > 4500 and (self.last_throttle - s.throttle) > 0.3:
            if random.random() < 0.4: s.backfire = True

        self.last_throttle = s.throttle
        if s.damaged: s.throttle = min(s.throttle, 0.5)
        
        base_torque = self.torque_at_rpm(s.rpm)
        
        if s.fuel_cut:
            effective_torque = -50.0 
        else:
            # Boost acts as a Multiplier on Torque
            boost_mult = 1.0 + (0.8 * s.boost) 
            effective_torque = base_torque * s.throttle * boost_mult

        self.update_turbo(dt)

        if s.current_gear == 0:
            rpm_acc = (effective_torque - (s.rpm * 0.1)) * dt * (1.0 / self.cfg.inertia)
            s.rpm += rpm_acc
        else:
            self.update_vehicle(effective_torque, dt)
            
        if s.rpm < self.cfg.idle_rpm:
            s.rpm += (self.cfg.idle_rpm - s.rpm) * 0.2

        # Heat
        heat = max(0, effective_torque) * s.throttle * self.cfg.overheat_rate
        cool = (s.coolant_temp - self.cfg.ambient_temp) * self.cfg.cooling_efficiency * dt * 0.3
        s.coolant_temp += (heat * dt) - cool

        if s.coolant_temp > self.cfg.max_coolant_temp:
            s.damaged = True
            s.limp_mode = True

    def set_throttle(self, val): self.state.throttle = max(0.0, min(1.0, val))
    def set_brake(self, val): self.state.brake_pedal = max(0.0, min(1.0, val))
    def set_load(self, val): self.state.load = max(0.0, min(1.0, val))
    def gear_up(self):
        if self.state.current_gear < len(self.cfg.gear_ratios) - 1: self.state.current_gear += 1
    def gear_down(self):
        if self.state.current_gear > 0: self.state.current_gear -= 1

    def get_state(self):
        s = self.state
        return {
            "time": s.time(), "rpm": s.rpm, "throttle": s.throttle,
            "gear": s.current_gear, "boost": s.boost,
            "torque": self.torque_at_rpm(s.rpm) * s.throttle * (1.0 + 0.8*s.boost),
            "afr": self.afr_estimate(s.rpm, s.throttle),
            "speed_kmh": s.speed * 3.6, "coolant_temp": s.coolant_temp,
            "limp_mode": s.limp_mode, "damaged": s.damaged,
            "backfire": s.backfire, "fuel_cut": s.fuel_cut, "brake": s.brake_pedal > 0
        }