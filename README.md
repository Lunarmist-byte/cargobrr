
# Cargobrr

Cargobrr is a real-time physics engine written in Python. It simulates internal combustion dynamics, turbocharging behaviors, thermal management, and vehicle inertia. The simulation visualizes this data through a custom-built dashboard featuring live telemetry and feedback systems.

## Installation

You need **Python 3.8** or newer.

1. Install the required dependencies:
   ```bash
   pip install pygame numpy
   ```

2.  Ensure your file structure places `engine.py` and `main.py` in the same directory (e.g., inside a `src/` folder).

## How to Run

To start the simulator, run the main script from your terminal:

```bash
python src/game.py
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
| **R** | Reset Simulation (Repairs Engine) |
| **ESC** | Quit Simulator |
| **Mouse Drag** | Adjust on-screen sliders (Throttle, Load, Redline) |

## Physics & Logic

### 1\. Turbocharger System

The engine utilizes a dynamic flow factor based on RPM to calculate boost pressure.

  * **Spool Up:** Occurs when the target boost is higher than the current boost. The rate of spooling is multiplied by RPM, meaning the turbo reacts faster at high revs.
  * **Blow Off:** When the throttle closes, boost pressure drops rapidly (calculated at 3x the spool rate).
  * **Torque Effect:** Boost pressure acts as a direct multiplier on the engine's base torque output (up to 1.8x at max boost).

### 2\. Hard-Cut Rev Limiter

Unlike simple limiters that clamp the RPM value, this system uses a fuel-cut strategy.

  * If RPM exceeds `Redline + 50`, the fuel cut activates, and torque becomes negative (-50 Nm).
  * Fuel delivery resumes only when RPM drops below `Redline - 150`.
  * This hysteresis loop creates a realistic "bouncing" effect against the limiter.

### 3\. Backfire System

  * **Trigger:** Rapid throttle release (greater than 30% drop) while RPM is high (above 4500).
  * **Effect:** There is a 40% probability per frame of unburnt fuel igniting in the exhaust.

### 4\. Thermal & Damage Model

  * **Heat Generation:** Proportional to Torque multiplied by Throttle position.
  * **Cooling:** Proportional to the difference between Coolant Temp and Ambient Temp, multiplied by efficiency.
  * **Limp Mode:** If coolant temperature exceeds 120°C, the engine enters Limp Mode. Throttle input is capped at 50% until the simulation is reset.

### 5\. Vehicle Inertia & Clutch

  * **Neutral (Gear 0):** The engine spins freely based solely on its internal rotational inertia (0.02).
  * **In Gear:** Engine RPM is mechanically linked to wheel speed using a blend factor (0.6 engine / 0.4 wheels). This simulates a solid clutch engagement. Drag, rolling resistance, and braking force (10,000 N) are applied directly to the vehicle mass.

## Default Configuration

The following values are defined in the `EngineConfig` class:

| Parameter | Value | Description |
| :--- | :--- | :--- |
| **Idle RPM** | 900 | Base idle speed |
| **Redline** | 7500 | Max RPM before fuel cut |
| **Max Boost** | 1.6 Bar | Maximum turbo pressure |
| **Vehicle Mass** | 1350 kg | Weight of the car |
| **Gear Ratios** | 3.8, 2.3, 1.5, 1.1, 0.9 | 1st through 5th gear ratios (Final Drive: 3.9) |
| **Drag Coeff** | 0.30 | Aerodynamic drag |
| **Brake Force** | 10,000 N | Force applied when holding Spacebar |
| **Coolant Max** | 120.0 °C | Threshold for permanent engine damage |

## Troubleshooting

  * **Lag or Freezing:** The simulation now uses a native graph implementation to eliminate lag caused by external plotting libraries. If you still experience low FPS on Windows, ensure you have not clicked inside the terminal window to select text, as this pauses script execution.
  * **Sound not playing:** Verify that the path provided in `ENGINE_SOUND_FILE` is an absolute path and that the file format is supported by Pygame (we recommend .wav or .ogg).

<!-- end list -->

```
```
