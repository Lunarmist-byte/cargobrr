# Cargobrr

A kinda good simulation (goes hard brr) of a car for future project testing. Simulates realistic internal combustion dynamics, turbocharging behaviors, thermal management, and vehicle inertia. The simulation visualizes this data through a custom-built dashboard featuring live telemetry and feedback systems.

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

## Installation

You need **Python 3.8** or newer.

1. Install the required dependencies:
   ```bash
   pip install pygame numpy numba
   ```
   or (run inside src)
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

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

### Optional: Engine Sound

To enable audio, you must set an environment variable pointing to a valid `.wav` or `.ogg` file before running the script.

**Windows (PowerShell):**

```powershell
$env:ENGINE_SOUND_FILE="path/to/engine_loop.wav"; python src/main.py
```

**Linux / macOS:**

```bash
ENGINE_SOUND_FILE=path/to/engine_loop.wav python src/main.py
```

## Controls

| Input | Action |
| :--- | :--- |
| **Arrow Up** | Increase Throttle |
| **Arrow Down** | Decrease Throttle |
| **Spacebar** | Apply Hydraulic Brakes |
| **Q** | Shift Gear Down |
| **E** | Shift Gear Up |
| **T** | Cycle Engine Profile (Displacement) |
| **B** | Cycle Engine Aspiration (NA, Turbo, Supercharger) |
| **R** | Reset Simulation (Repairs Engine) |
| **ESC** | Quit Simulator |
| **Mouse Drag** | Adjust on-screen sliders (Throttle, Load, Redline) |

## Physics & Logic

### 1. Turbocharger System

The engine utilizes a dynamic flow factor based on RPM to calculate boost pressure.

  * **Spool Up:** Occurs when the target boost is higher than the current boost. The rate of spooling is multiplied by RPM, meaning the turbo reacts faster at high revs.
  * **Blow Off:** When the throttle closes, boost pressure drops rapidly (calculated at 3x the spool rate).
  * **Torque Effect:** Boost pressure acts as a direct multiplier on the engine's base torque output (up to 1.8x at max boost).

### 2. Hard-Cut Rev Limiter

Unlike simple limiters that clamp the RPM value, this system uses a fuel-cut strategy.

  * If RPM exceeds `Redline + 50`, the fuel cut activates, and torque becomes negative (-50 Nm).
  * Fuel delivery resumes only when RPM drops below `Redline - 150`.
  * This hysteresis loop creates a realistic "bouncing" effect against the limiter.

### 3. Backfire System

  * **Trigger:** Rapid throttle release (greater than 30% drop) while RPM is high (above 4500).
  * **Effect:** There is a 40% probability per frame of unburnt fuel igniting in the exhaust.

### 4. Thermal & Damage Model

  * **Heat Generation:** Proportional to Torque multiplied by Throttle position.
  * **Cooling:** Proportional to the difference between Coolant Temp and Ambient Temp, multiplied by efficiency.
  * **Limp Mode:** If coolant temperature exceeds 120°C, the engine enters Limp Mode. Throttle input is capped at 50% until the simulation is reset.

### 5. Vehicle Inertia & Clutch

  * **Neutral (Gear 0):** The engine spins freely based solely on its internal rotational inertia (0.02).
  * **In Gear:** Engine RPM is mechanically linked to wheel speed using a blend factor (0.6 engine / 0.4 wheels). This simulates a solid clutch engagement. Drag, rolling resistance, and braking force (10,000 N) are applied directly to the vehicle mass.

## Troubleshooting

  * **Lag or Freezing:** If you still experience low FPS on Windows, ensure you have not clicked inside the terminal window to select text, as this pauses script execution.
  * **Sound not playing:** Verify that the path provided in `ENGINE_SOUND_FILE` is an absolute path and that the file format is supported by Pygame (we recommend .wav or .ogg).

## Images
<img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/67dd7717-0175-403c-8bac-8aba33e9b64e" />
<img width="500" height="500" alt="Screenshot 2025-11-30 195801" src="https://github.com/user-attachments/assets/0e915450-1ca3-4ce6-8c0c-e0f87df0b297" />
