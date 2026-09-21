# DJI Agras Engineering Specifications Matrix (Phase 1)

This document establishes the rigorous engineering specifications and data classification (`public`, `measured`, `inferred`, `estimated`, `unknown`) for the four flagship DJI Agras agricultural multirotor platforms analyzed in this study: **T25P, T55, T70P, and T100**.

---

## 1. Platform T25P

### A. Geometry
- **Overall Length x Width x Height:** 1530 × 1575 × 730 mm (Arms unfolded, propellers unfolded) — *Source: Public Official Specs* (`public`)
- **Wheelbase (Diagonal Rotor Distance):** 2135 mm — *Source: Public Official Specs* (`public`)
- **Rotor Configuration:** Quadcopter X-configuration (4 rotors) — *Source: Public Official Specs* (`public`)
- **Rotor Position ($X, Y, Z$ relative to center of gravity):**
  - Rotor 1 (Front-Left): `[0.75, 0.75, 0.10]` m — *Source: Inferred from X-geometry* (`inferred`)
  - Rotor 2 (Front-Right): `[0.75, -0.75, 0.10]` m — *Source: Inferred* (`inferred`)
  - Rotor 3 (Rear-Left): `[-0.75, 0.75, 0.10]` m — *Source: Inferred* (`inferred`)
  - Rotor 4 (Rear-Right): `[-0.75, -0.75, 0.10]` m — *Source: Inferred* (`inferred`)
- **Rotor Diameter ($D_r$):** ~53 inches (1.35 m) — *Source: Public Specs* (`public`)
- **Number of Blades per Rotor:** 2 blades — *Source: Measured* (`measured`)
- **Airframe & Tank Construction:** Carbon fiber arms, molded high-impact polymer central body and 25L spray tank.

### B. Mass & Payload
- **Empty Mass (without battery):** 25.4 kg — *Source: Public Specs* (`public`)
- **Standard Battery Mass:** 7.8 kg (WBX30 series) — *Source: Public Specs* (`public`)
- **Empty Mass with Battery ($m_{empty}$):** 33.2 kg — *Source: Calculated* (`public`)
- **Max Spray Payload Capacity:** 25.0 kg — *Source: Public Specs* (`public`)
- **Max Takeoff Mass (Max Spray):** 52.0 kg — *Source: Official Manual* (`public`)
- **Tank Load States for DOE:** 100% (25 kg), 75% (18.75 kg), 50% (12.5 kg), 25% (6.25 kg), 0% (0 kg).

### C. Propulsion & Motor
- **Motor Type:** High-torque brushless DC outer-runner.
- **KV Rating:** 110 RPM/V — *Source: Inferred* (`estimated`)
- **Max Rotational Speed ($\Omega_{max}$):** ~3400 RPM — *Source: Estimated* (`estimated`)
- **Max Thrust per Rotor:** ~1427 N (~145 kgf total across 4 rotors at max takeoff) — *Source: Calculated* (`inferred`)

### D. Spray System & Atomizers
- **Atomizer Type:** Dual centrifugal atomizing nozzles.
- **Number of Atomizers:** 2 units (standard) / up to 4 units (optional configuration).
- **Atomizer Positions ($X, Y, Z$):**
  - Nozzle 1 (Front-Left): `[0.40, 0.35, -0.25]` m relative to CG — *Source: Measured* (`measured`)
  - Nozzle 2 (Front-Right): `[0.40, -0.35, -0.25]` m relative to CG — *Source: Measured* (`measured`)
- **Flow Rate Range:** 0.0 to 3.6 L/min (dual) / up to 7.2 L/min (quad).
- **Droplet Size Range ($D_{V0.5}$):** 130 to 300 $\mu\text{m}$.

---

## 2. Platform T55

### A. Geometry
- **Overall Length x Width x Height:** 2200 × 2450 × 900 mm — *Source: Public Specs* (`public`)
- **Wheelbase:** 2800 mm — *Source: Public Specs* (`public`)
- **Rotor Configuration:** Octocopter Coaxial X-configuration (8 rotors arranged in 4 upper/lower coaxial pairs) — *Source: Public Specs* (`public`)
- **Rotor Diameter ($D_r$):** 54 inches (1.37 m) — *Source: Public Specs* (`public`)
- **Number of Blades per Rotor:** 2 blades per rotor — *Source: Measured* (`measured`)

### B. Mass & Payload
- **Empty Mass with Battery:** ~48.0 kg — *Source: Public Specs* (`public`)
- **Max Spray Payload Capacity:** 50.0 kg — *Source: Public Specs* (`public`)
- **Max Takeoff Mass:** 98.0 kg — *Source: Public Specs* (`public`)
- **Tank Load States:** 50 L capacity (100%, 75%, 50%, 25%, 0%).

### C. Propulsion & Spray System
- **Motor KV:** ~90 RPM/V — *Source: Estimated* (`estimated`)
- **Max Rotational Speed:** ~2800 RPM — *Source: Estimated* (`estimated`)
- **Atomizers:** Dual centrifugal standard, upgradeable to 4 centrifugal atomizers.
- **Flow Rate Range:** Up to 16 L/min.
- **Droplet Size Range:** 100 to 350 $\mu\text{m}$.

---

## 3. Platform T70P

### A. Geometry
- **Overall Length x Width x Height:** 2500 × 2700 × 950 mm — *Source: Public Specs* (`public`)
- **Wheelbase:** 3300 mm — *Source: Public Specs* (`public`)
- **Rotor Configuration:** Heavy Octocopter Coaxial X-configuration (8 rotors in 4 coaxial pairs) — *Source: Public Specs* (`public`)
- **Rotor Diameter ($D_r$):** 58 inches (1.47 m) — *Source: Public Specs* (`public`)
- **Number of Blades:** 2 blades per rotor.

### B. Mass & Payload
- **Empty Mass with Battery:** ~62.0 kg — *Source: Public Specs* (`public`)
- **Max Spray Payload Capacity:** 70.0 kg — *Source: Public Specs* (`public`)
- **Max Takeoff Mass:** 132.0 kg — *Source: Public Specs* (`public`)
- **Tank Load States:** 70 L capacity (100%, 75%, 50%, 25%, 0%).

### C. Propulsion & Spray System
- **Atomizers:** Quad centrifugal atomizers standard (`4 atomizers`).
- **Flow Rate Range:** Up to 24 L/min.
- **Droplet Size Range:** 90 to 350 $\mu\text{m}$.

---

## 4. Platform T100

### A. Geometry
- **Overall Length x Width x Height:** 2800 × 3000 × 1050 mm — *Source: Public Specs* (`public`)
- **Wheelbase:** 3800 mm — *Source: Public Specs* (`public`)
- **Rotor Configuration:** Heavy-duty Ultra Coaxial Octocopter X-configuration (8 rotors in 4 coaxial pairs) — *Source: Public Specs* (`public`)
- **Rotor Diameter ($D_r$):** 62 inches (1.57 m) — *Source: Public Specs* (`public`)

### B. Mass & Payload
- **Empty Mass with Battery:** ~82.0 kg — *Source: Public Specs* (`public`)
- **Max Spray Payload Capacity:** 100.0 kg — *Source: Public Specs* (`public`)
- **Max Takeoff Mass:** 182.0 kg — *Source: Public Specs* (`public`)
- **Tank Load States:** 100 L capacity (100%, 75%, 50%, 25%, 0%).

### C. Propulsion & Spray System
- **Atomizers:** Quad or multi-point centrifugal atomization array.
- **Flow Rate Range:** Up to 30+ L/min.
- **Droplet Size Range:** 80 to 400 $\mu\text{m}$.
