# VR_SIMULATED_RIDING_SETUP_AND_DOCUMENTATION

# GROUP MEMBERS AND ROLES
Ebong Jesse

Ntumwe Raymond

Morris A Rice

Joshua Jolly

Mathilda Hilda

Magezi Richard



**Overview:** This project converts a standard bicycle into an interactive VR fitness rig by using a rear-wheel trainer stand to keep the bike stationary while an AS5600 magnetic encoder and ESP32 microcontroller track the roller shaft's rotation, sending real-time speed data wirelessly via Wi-Fi or Bluetooth to a Meta Quest 3 headset. Built with Unity or Unreal Engine, the VR software translates physical pedaling directly into 1:1 forward motion through immersive virtual environments, incorporating smooth speed filtering, high frame rates, and cooling airflow to minimize motion sickness, while gamifying the ride with live HUD metrics, checkpoints, and leaderboards.

---

# VR Bicycle Setup Requirements

## 1. Mechanical & Hardware
* **Bicycle:** Standard mechanical bicycle.
* **Bike Trainer Stand (Turbo Trainer):** Clamps the rear axle and provides wheel resistance (magnetic, fluid, or roller-type).
* **Front Wheel Riser Block:** Levels the bike frame (can be manufactured or improvised using wood).
* **Floor Area & Clear Area:** Provides a stable footprint and creates a safe perimeter free of nearby physical hazards.
* **Sensor Mounting Bracket:** Custom 3D-printed or fabricated mount to secure the AS5600 sensor to the trainer roller shaft end.


## 2. Sensing & Electronics
* **Core Microcontroller:** ESP32 board (provides I2C reading and Wi-Fi/Bluetooth capabilities).
* **Rotary Angle Sensor:** AS5600 magnetic encoder module.
* **Magnet:** 6 mm × 2–3 mm **diametrically magnetized** neodymium disc magnet (mounted on the rotating shaft end).
* **Brake Sensor (Recommended):** Microswitch or reed switch mounted on the brake lever.
* **Power Supply:** 5V USB power bank or external AC adapter for the ESP32.
* **Cablings & Prototyping:** Jumper wires, breadboard/perfboard, zip ties, and cable management sleeves.
* *(Optional)* **Steering Tracking:** 
  * Quest controller handlebar mount **OR**
  * Secondary AS5600 sensor with a TCA9548A I2C multiplexer (or mapped to ESP32's secondary I2C bus).
* *(Optional)* **Resistance Control:** Servo motor configured to drive the trainer resistance lever.

## 3. Headset & VR Equipment
* **VR Headset:** Meta Quest 3.
* **Facial Interface:** Cleanable silicone face cover for sweat management.
* **Environmental Comfort:** External electric fan directed at the rider.

## 4. Software & Integration
* **Development Engine:** Unity or Unreal Engine application targeting Meta Quest 3.
* **Communication Protocol:** 
  * Wi-Fi (UDP or WebSockets) **OR**
  * Bluetooth Low Energy (using standard FTMS or Cycling Speed and Cadence profiles).
* **Data Processing:** Moving average window algorithm on the ESP32 or Unity side for speed signal smoothing.
* **Graphics Pipeline:** World Labs Marble terrain scenes (optimized for 72+ FPS performance).

## 5. Comfort & Motion Safety Features
* 1:1 ratio between physical pedaling speed and in-game visual forward movement.
* Comfort vignette (dynamic edge-darkening) enabled during directional turns.
* Smooth, fixed camera height without artificial camera bumps or uninitiated rotation.

## 6. Gamification Features
* On-Screen Display (HUD) showing current speed, distance, elapsed time, and estimated calorie burn.
* Checkpoint system, collectibles, and local/online leaderboards along the path.

# VR Bicycle System Operational Flow
## Sequential Execution Breakdown

### 1. Mechanical Input Generation
1. The rider sits on the stationary bicycle and begins pedaling.
2. Power transfers through the bike chain to turn the rear wheel.
3. The rear tire drives the clamped trainer roller, causing the roller shaft to spin proportionally to actual wheel speed.

### 2. Physical Sensing & Signal Acquisition
1. A diametrically magnetized neodymium magnet attached to the roller shaft rotates synchronously with the wheel.
2. The fixed AS5600 magnetic encoder detects the changing magnetic field orientation across its surface without physical contact.
3. Raw angular displacement data is transmitted continuously to the ESP32 via the I2C protocol.

### 3. Onboard Processing (ESP32)
1. **RPM & Speed Calculation:** The ESP32 converts angular changes over time into roller RPM, then computes linear ground speed ($v = \text{roller RPM} \times \text{roller circumference}$).
2. **Filtering:** Raw velocity values pass through a moving average window to smooth out vibration-induced noise and mechanical jitter.
3. **Transmission:** Processed speed packets are packaged and sent wirelessly over Wi-Fi (UDP/WebSockets) or Bluetooth Low Energy (FTMS profile).

### 4. VR Rendering & Feedback (Meta Quest 3)
1. **Packet Reception:** The Unity or Unreal Engine application on the Quest 3 ingests the incoming wireless telemetry stream.
2. **Locomotion Mapping:** In-game player velocity is updated continuously to match physical speed at a 1:1 scale.
3. **Visual Output:** The virtual camera moves forward through the 3D environment, maintaining a frame rate of at least 72 FPS to prevent latency-induced motion sickness.
4. **HUD & Gamification:** The head-up display updates live metrics (speed, distance, calories, elapsed time) while tracking checkpoints and collectibles along the route.

### 5. Closed-Loop Rider Sensory Feedback
1. **Visual Match:** Visual forward motion directly mirrors the rider's physical pedaling cadence.

2. **Optional Steering/Braking:** Handlebar input adjusts the virtual trajectory, while microswitches on the brake levers trigger in-game deceleration.
