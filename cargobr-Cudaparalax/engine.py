import math
import numpy as np
import time
import random
from numba import cuda, float32, int32

@cuda.jit(device=True)
def get_ve_cuda(rpm, map_rpms, map_ves, map_len):
    '''Dynamic Volumetric Efficiency Reader from VRAM'''
    if rpm <= map_rpms[0]: return map_ves[0]
    if rpm >= map_rpms[map_len-1]: return map_ves[map_len-1]
    for i in range(map_len -1):
        if rpm >= map_rpms[i] and rpm <= map_rpms[i+1]:
            return map_ves[i] + (rpm - map_rpms[i]) * (map_ves[i+1] - map_ves[i]) / (map_rpms[i+1] - map_rpms[i])
    return 0.0

@cuda.jit
def engine_swarm_kernel(rpm, throttle, last_throttle, load, current_gear, boost, coolant_temp, speed, fuel_cut, backfire, brake_pedal, damaged, limp_mode, gear_ratios, dt, n, idle_rpm, redline, inertia, final_drive, max_boost_bar, vehicle_mass, wheel_radius, drag_coefficient, frontal_area, air_density, overheat_rate, cooling_efficiency, ambient_temp, max_coolant_temp, map_rpms, map_ves, map_len, displacement_l, turbo_inertia):
    i = cuda.grid(1)
    if i >= n: return
    
    if rpm[i] > redline + 50.0: fuel_cut[i] = True
    elif fuel_cut[i] and rpm[i] < redline - 150.0: fuel_cut[i] = False
    
    backfire[i] = False
    if rpm[i] > 4500.0 and (last_throttle[i] - throttle[i]) > 0.3:
        if i % 10 < 4: backfire[i] = True
        
    last_throttle[i] = throttle[i]
    if damaged[i]: throttle[i] = min(throttle[i], 0.5)
    
    ve = get_ve_cuda(rpm[i], map_rpms, map_ves, map_len)
    
    # Base torque calculation purely from air processing
    base_torque = (displacement_l * ve * air_density * 1000.0) / (4.0 * 3.14159)
    
    # Heat soak penalty
    temp_delta = max(0.0, coolant_temp[i] - 90.0)
    heat_penalty = max(0.6, 1.0 - (temp_delta * 0.01))
    
    dyn_torque = base_torque * heat_penalty

    if fuel_cut[i]: 
        effective_torque = -50.0
    else: 
        effective_torque = dyn_torque * throttle[i] * (1.0 + (0.8 * boost[i]))

    rpm_frac = rpm[i] / redline
    target_boost = throttle[i] * max_boost_bar * min(1.0, rpm_frac * 1.5)

    if target_boost > boost[i]:
        boost[i] += (target_boost - boost[i]) * dt * ((1.0 / turbo_inertia) * (1.0 + rpm_frac))
    else: 
        boost[i] += (target_boost - boost[i]) * dt * 3.0

    gear_ratio = gear_ratios[current_gear[i]]
    if current_gear[i] == 0:
        rpm[i] += (effective_torque - (rpm[i] * 0.1)) * dt * (1.0 / inertia)
    else:
        wheel_force = (effective_torque * gear_ratio * final_drive) / wheel_radius
        aero = 0.5 * air_density * drag_coefficient * frontal_area * (speed[i]**2)
        net_force = wheel_force - (aero + (9.81 * 0.015 * vehicle_mass) + (load[i] * 2000.0) + (brake_pedal[i] * 10000.0))
        speed[i] = max(0.0, speed[i] + (net_force / vehicle_mass) * dt)
        target_rpm = ((speed[i] / (2.0 * 3.14159 * wheel_radius)) * 60.0) * gear_ratio * final_drive
        rpm[i] = (rpm[i] * 0.6) + (target_rpm * 0.4)
        
    if rpm[i] < idle_rpm: rpm[i] += (idle_rpm - rpm[i]) * 0.2
    
    coolant_temp[i] += ((max(0.0, effective_torque) * throttle[i] * overheat_rate * dt) - ((coolant_temp[i] - ambient_temp) * cooling_efficiency * dt * 0.3))
    
    if coolant_temp[i] > max_coolant_temp:
        damaged[i] = True
        limp_mode[i] = True

class EngineConfig:
    def __init__(self, engine_type="2.0L", aspiration="Stock"):
        self.engine_type = engine_type
        self.aspiration = aspiration
        self.ambient_temp = 25.0
        self.max_coolant_temp = 120.0
        self.overheat_rate = 0.08
        self.cooling_efficiency = 0.6
        self.air_density = 1.225
        self.vehicle_mass = 1350.0
        self.wheel_radius = 0.33
        self.drag_coefficient = 0.30
        self.frontal_area = 2.2
        self.final_drive = 3.9
        self.gear_ratios = np.array([0.0, 3.8, 2.3, 1.5, 1.1, 0.9], dtype=np.float32)

        if engine_type == "2.0L":
            self.idle_rpm = 900.0
            self.redline = 7500.0
            self.inertia = 0.02
            self.max_boost_bar = 1.6
            self.turbo_inertia = 0.2
            self.displacement_l = 2.0
            self.base_ve = 0.85
            self.volumetric_eff_map = np.array([[800, 0.70], [2500, 0.85], [4500, 0.92], [5500, 0.90], [7500, 0.78], [8000, 0.60]], dtype=np.float32)
        elif engine_type == "3.0L":
            self.idle_rpm = 800.0
            self.redline = 7000.0
            self.inertia = 0.025
            self.max_boost_bar = 1.2
            self.turbo_inertia = 0.3
            self.displacement_l = 3.0
            self.base_ve = 0.88
            self.volumetric_eff_map = np.array([[800, 0.75], [2000, 0.90], [4000, 0.95], [5500, 0.90], [7000, 0.75], [8000, 0.50]], dtype=np.float32)
        elif engine_type == "5.0L":
            self.idle_rpm = 650.0
            self.redline = 6500.0
            self.inertia = 0.035
            self.max_boost_bar = 0.0
            self.turbo_inertia = 99.0
            self.displacement_l = 5.0
            self.base_ve = 0.92
            self.volumetric_eff_map = np.array([[650, 0.85], [1500, 0.94], [3500, 0.98], [5000, 0.95], [6500, 0.80], [7000, 0.60]], dtype=np.float32)
        elif engine_type == "1.0L":
            self.idle_rpm = 800.0
            self.redline = 6000.0
            self.inertia = 0.012
            self.max_boost_bar = 0.0
            self.turbo_inertia = 99.0
            self.displacement_l = 1.0
            self.base_ve = 0.80
            self.volumetric_eff_map = np.array([[800, 0.65], [2000, 0.85], [3500, 0.90], [4500, 0.85], [5500, 0.70], [6000, 0.55]], dtype=np.float32)
        elif engine_type == "1.6L":
            self.idle_rpm = 1000.0
            self.redline = 8500.0
            self.inertia = 0.015
            self.max_boost_bar = 2.0
            self.turbo_inertia = 0.15
            self.displacement_l = 1.6
            self.base_ve = 0.82
            self.volumetric_eff_map = np.array([[1000, 0.60], [3000, 0.80], [5000, 0.95], [6500, 0.98], [8000, 0.90], [9000, 0.75]], dtype=np.float32)
        elif engine_type == "4.0L":
            self.idle_rpm = 900.0
            self.redline = 9000.0
            self.inertia = 0.022
            self.max_boost_bar = 0.0
            self.turbo_inertia = 99.0
            self.displacement_l = 4.0
            self.base_ve = 0.95
            self.volumetric_eff_map = np.array([[900, 0.80], [3000, 0.90], [5500, 1.05], [7500, 1.10], [8500, 1.05], [9500, 0.85]], dtype=np.float32)
        elif engine_type == "6.2L":
            self.idle_rpm = 700.0
            self.redline = 6200.0
            self.inertia = 0.040
            self.max_boost_bar = 1.0
            self.turbo_inertia = 0.05
            self.displacement_l = 6.2
            self.base_ve = 0.90
            self.volumetric_eff_map = np.array([[700, 0.85], [2000, 0.95], [3500, 1.0], [5000, 0.98], [6200, 0.85], [6500, 0.60]], dtype=np.float32)
        elif engine_type == "8.0L":
            self.idle_rpm = 800.0
            self.redline = 7000.0
            self.inertia = 0.050
            self.max_boost_bar = 1.8
            self.turbo_inertia = 0.5
            self.displacement_l = 8.0
            self.base_ve = 0.85
            self.volumetric_eff_map = np.array([[800, 0.75], [2500, 0.88], [4500, 0.96], [6000, 0.94], [7000, 0.80], [7500, 0.60]], dtype=np.float32)
        else:
            self.idle_rpm = 900.0
            self.redline = 7500.0
            self.inertia = 0.02
            self.max_boost_bar = 1.6
            self.turbo_inertia = 0.2
            self.displacement_l = 2.0
            self.base_ve = 0.85
            self.volumetric_eff_map = np.array([[800, 0.70], [2500, 0.85], [4500, 0.92], [5500, 0.90], [7500, 0.78], [8000, 0.60]], dtype=np.float32)

        # Aspiration Modifier
        if self.aspiration == "NA":
            self.max_boost_bar = 0.0
            self.turbo_inertia = 99.0
        elif self.aspiration == "Turbo":
            self.max_boost_bar = max(1.2, self.max_boost_bar)
            self.turbo_inertia = 0.3
        elif self.aspiration == "SC":
            self.max_boost_bar = max(0.8, self.max_boost_bar * 0.8)
            self.turbo_inertia = 0.05

class Engine:
    def __init__(self, cfg=None, num_engines=10000):
        self.cfg = cfg or EngineConfig()
        self.n = num_engines
        self._start_time = time.time()

        self.base_rpms = self.cfg.volumetric_eff_map[:, 0]
        self.base_ves = self.cfg.volumetric_eff_map[:, 1]
        self.map_len = len(self.base_rpms)

        self.d_rpm = cuda.to_device(np.full(self.n, self.cfg.idle_rpm, dtype=np.float32))
        self.d_throttle = cuda.to_device(np.zeros(self.n, dtype=np.float32))
        self.d_last_throttle = cuda.to_device(np.zeros(self.n, dtype=np.float32))
        self.d_load = cuda.to_device(np.zeros(self.n, dtype=np.float32))
        self.d_current_gear = cuda.to_device(np.ones(self.n, dtype=np.int32))
        self.d_boost = cuda.to_device(np.zeros(self.n, dtype=np.float32))
        self.d_coolant_temp = cuda.to_device(np.full(self.n, self.cfg.ambient_temp, dtype=np.float32))
        self.d_speed = cuda.to_device(np.zeros(self.n, dtype=np.float32))

        self.d_fuel_cut = cuda.to_device(np.zeros(self.n, dtype=np.int8))
        self.d_backfire = cuda.to_device(np.zeros(self.n, dtype=np.int8))
        self.d_brake_pedal = cuda.to_device(np.zeros(self.n, dtype=np.float32))
        self.d_damaged = cuda.to_device(np.zeros(self.n, dtype=np.int8))
        self.d_limp_mode = cuda.to_device(np.zeros(self.n, dtype=np.int8))
        self.d_gear_ratios = cuda.to_device(self.cfg.gear_ratios)

        self.d_map_rpms = cuda.to_device(self.base_rpms)
        self.d_map_ves = cuda.to_device(self.base_ves)

        self.threads_per_block = 256
        self.blocks_per_grid = (self.n + (self.threads_per_block - 1)) // self.threads_per_block

    def tune_ecu(self, new_ves):
        '''flashes new VE array to gpu'''
        self.base_ves = np.array(new_ves, dtype=np.float32)
        self.d_map_ves.copy_to_device(self.base_ves)

    def update(self, dt):
        engine_swarm_kernel[self.blocks_per_grid, self.threads_per_block](
            self.d_rpm, self.d_throttle, self.d_last_throttle, self.d_load, self.d_current_gear, 
            self.d_boost, self.d_coolant_temp, self.d_speed, self.d_fuel_cut, self.d_backfire, 
            self.d_brake_pedal, self.d_damaged, self.d_limp_mode, self.d_gear_ratios, float(dt), 
            self.n, self.cfg.idle_rpm, self.cfg.redline, self.cfg.inertia, self.cfg.final_drive, 
            self.cfg.max_boost_bar, self.cfg.vehicle_mass, self.cfg.wheel_radius, self.cfg.drag_coefficient, 
            self.cfg.frontal_area, self.cfg.air_density, self.cfg.overheat_rate, self.cfg.cooling_efficiency, 
            self.cfg.ambient_temp, self.cfg.max_coolant_temp, self.d_map_rpms, self.d_map_ves, self.map_len, 
            self.cfg.displacement_l, self.cfg.turbo_inertia
        )

    def set_throttle(self, val): self.d_throttle.copy_to_device(np.full(self.n, max(0.0, min(1.0, val)), dtype=np.float32))
    def set_brake(self, val): self.d_brake_pedal.copy_to_device(np.full(self.n, max(0.0, min(1.0, val)), dtype=np.float32))
    
    def gear_up(self):
        cg = self.d_current_gear.copy_to_host()[0]
        if cg < len(self.cfg.gear_ratios) - 1: self.d_current_gear.copy_to_device(np.full(self.n, cg + 1, dtype=np.int32))
        
    def gear_down(self):    
        cg = self.d_current_gear.copy_to_host()[0]
        if cg > 0: self.d_current_gear.copy_to_device(np.full(self.n, cg - 1, dtype=np.int32))
        
    def get_state(self, index=0):
        rpm = self.d_rpm.copy_to_host()[index]
        throttle = self.d_throttle.copy_to_host()[index]
        return {
            "time": time.time() - self._start_time, "rpm": rpm, "throttle": throttle, 
            "gear": self.d_current_gear.copy_to_host()[index], "boost": self.d_boost.copy_to_host()[index],
            "afr": 14.7 - (3.5 * throttle), "speed_kmh": self.d_speed.copy_to_host()[index] * 3.6,
            "coolant_temp": self.d_coolant_temp.copy_to_host()[index],
            "limp_mode": bool(self.d_limp_mode.copy_to_host()[index]), "damaged": bool(self.d_damaged.copy_to_host()[index]),
            "backfire": bool(self.d_backfire.copy_to_host()[index]), "fuel_cut": bool(self.d_fuel_cut.copy_to_host()[index]),
            "brake": bool(self.d_brake_pedal.copy_to_host()[index] > 0)
        }
