# Cargobrr

A kinda good simulation (goes hard brr) of a car for future project testing. Simulates realistic engine physics, torque calculations, and aerodynamics. 

## Features
- **Dynamic Torque Map**: Calculates realistic torque based on Engine Displacement, Volumetric Efficiency (VE), Heat Soak, and Air Density.
- **Engine Profiles**: Choose between 8 different engines on the fly!
  - `1.0L` (Economy I3)
  - `1.6L` (Rally I4)
  - `2.0L` (Turbo I4)
  - `3.0L` (Twin-Turbo I6)
  - `4.0L` (High-revving Flat-6)
  - `5.0L` (NA V8)
  - `6.2L` (Supercharged V8)
  - `8.0L` (Quad-Turbo W16)
- **Aspiration Swapping**: Change any engine's forced induction system dynamically!
  - `Stock`: The engine's built-in aspiration.
  - `NA`: Naturally Aspirated.
  - `Turbo`: Exhaust-driven turbocharger (features turbo lag).
  - `SC`: Belt-driven supercharger (instant spooling).
- **CUDA Swarm Simulator**: Includes a Numba CUDA implementation (`cargobr-Cudaparalax`) capable of simulating 10,000 engines in parallel on the GPU with the exact same physics as the standard Python version.

## Controls
- `UP/DOWN Arrows`: Control Throttle
- `SPACE`: Brake
- `Q / E`: Gear Down / Gear Up
- `T`: Cycle Engine Profile (Displacement)
- `B`: Cycle Engine Aspiration (NA, Turbo, Supercharger)
- `R`: Reset Engine
- `ESC`: Quit

## Running
Standard Version:
```bash
cd src
python main.py
```
CUDA Parallel Version (Requires Numba/CUDA):
```bash
cd cargobr-Cudaparalax
python main.py
```
