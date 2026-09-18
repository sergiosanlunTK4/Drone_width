# RESEARCH_ARCHITECTURE_V1.md

## 1. Problem Definition
Agricultural multirotor unmanned aerial vehicles (UAVs) have revolutionized precision crop protection. However, operational deployment currently relies heavily on empirical tuning, nominal manufacturer widths (e.g., fixed effective swath assumptions), and simplified single-variable guidelines. These approximations fail to capture the complex fluid-structure interactions, rotor wake interference, dynamic payload mass reduction during tank emptying, and multi-variable coupling among forward flight speed ($V_\infty$), flight altitude ($H$), droplet size distribution ($D_{V0.5}$), and atomizer spatial configuration. 

This research establishes a rigorous, physics-based, multi-fidelity computational fluid dynamics (CFD) and Lagrangian particle tracking framework to characterize and predict the 3D aerodynamic flow field, rotor downwash, droplet transport physics, and spatio-temporal deposition patterns $D(x,y,t)$ across four flagship DJI Agras platforms: **T25P, T55, T70P, and T100**.

---

## 2. Scientific Relevance
Understanding agricultural drone spray deposition requires bridging rotor aerodynamics and multi-phase fluid mechanics:
1. **Rotor Wake Dynamics:** Multi-rotor interference creates complex downwash contraction, tip vortices, and turbulent kinetic energy ($TKE$) distributions that dictate droplet dispersion.
2. **Droplet-Turbulence Coupling:** Particle Stokes numbers ($St$) and particle Reynolds numbers ($Re_p$) determine whether droplets faithfully follow fluid streamlines or cross them via inertial ballistics.
3. **Operational Optimization:** Moving beyond static swath rules enables multi-objective operational modes balancing spatial uniformity ($CV$), productivity (hectares/hour), and ecological efficiency (minimizing off-target drift and over-application).

---

## 3. Literature Gap
Current literature predominantly focuses on:
- Single UAV platforms (older models like T16, T20, T30, T40).
- Simplified Actuator Disk approximations without explicit rotor blade kinematics or realistic airframe blockage.
- Empirical regression models tied to specific crop canopies or wind conditions, lacking generalizability.
- **Identified Gaps Addressed Herein:**
  - Comparative multi-platform aerodynamic analysis across modern heavy-payload DJI Agras configurations (T25P, T55, T70P, T100).
  - Explicit evaluation of atomizer number (2 vs. 4) and spatial positioning relative to rotor slipstreams.
  - Rigorous quantification of dynamic payload mass reduction $m(t)$ on downwash velocity and integrated deposition $D_{avg}(x,y)$.
  - Open, fully reproducible open-source CFD and surrogate modeling workflows.

---

## 4. Novelty Hypothesis
- **Direct Multi-Platform Contrast:** Demonstrates that platform architecture (hexacopter vs. octocopter coaxial/coplanar arrangements, disk loading, and spatial dimensions) produces fundamentally distinct downwash velocity profiles and deposition signatures, falsifying the hypothesis of a universal scaling law.
- **Spatial Atomizer Interaction:** Proves that positioning atomizers directly within high-velocity rotor slipstreams versus peripheral wakes significantly alters droplet entrainment and transverse deposition symmetry.
- **Surrogate-Enabled Mobile Intelligence:** Establishes that Gaussian Process Regression (GPR) models trained on validated CFD datasets can reproduce high-resolution deposition metrics with high accuracy ($R^2 > 0.92$) and quantifiable epistemic uncertainty, suitable for offline mobile application deployment.

---

## 5. Scope
- Four independent UAV models: DJI Agras T25P, T55, T70P, T100.
- Standardized atmospheric reference: $T = 28\ ^\circ\text{C}$, $RH = 70\%$, $V_{wind} = 0\text{ m/s}$, Altitude $0\text{ m}$ (ISA standard pressure), pure water fluid properties ($\rho = 996.2\text{ kg/m}^3$, $\mu = 8.52 \times 10^{-4}\text{ Pa}\cdot\text{s}$, $\sigma = 0.0717\text{ N/m}$).
- Comprehensive parameter space: Flight velocity ($V_\infty$), flight altitude ($H$), droplet size ($D_{V0.5}$), payload mass fraction ($m/m_{max}$), and atomizer configurations (2 vs. 4 nozzles, front/rear/outboard placements).

---

## 6. Out-of-Scope Variables (Initial Phase)
To isolate UAV aerodynamic and operational variables, the following are explicitly excluded from the primary study and reserved for future work:
- Crosswinds, atmospheric turbulence, and thermal stratification.
- Pesticides, adjuvants, surfactants, oil emulsions, and non-Newtonian fluid rheology.
- Crop canopy drag, foliage interception, leaf boundary layer deposition, and sub-canopy microclimate.
- Complex topography and terrain-following ground effects.

---

## 7. Four UAV Comparison Matrix

| Feature / Parameter | DJI Agras T25P | DJI Agras T55 | DJI Agras T70P | DJI Agras T100 |
| :--- | :--- | :--- | :--- | :--- |
| **Configuration Type** | Hexacopter (Foldable) | Octocopter (Coaxial / Dual) | Octocopter (Heavy Coaxial) | Heavy Octocopter (Ultra Coaxial) |
| **Empty Mass ($m_{empty}$)** | *Inferred / Public (~25 kg)* | *Inferred / Public (~38 kg)* | *Inferred / Public (~52 kg)* | *Inferred / Public (~68 kg)* |
| **Max Takeoff Mass (Spray)** | *Public (~50 kg)* | *Public (~95 kg)* | *Public (~120 kg)* | *Public (~150 kg)* |
| **Max Payload Capacity** | *Public (25 kg)* | *Public (50 kg)* | *Public (70 kg)* | *Public (100 kg)* |
| **Rotor Count & Diameter** | 6 rotors, ~50 inches | 8 rotors (coaxial), ~54 in | 8 rotors (coaxial), ~58 in | 8 rotors (heavy coaxial), ~62 in |
| **Max Thrust per Rotor** | *Inferred / Estimated* | *Inferred / Estimated* | *Inferred / Estimated* | *Inferred / Estimated* |
| **Tank Capacity** | 25 L | 50 L | 70 L | 100 L |
| **Atomizer System** | Centrifugal (Dual) | Centrifugal (Dual/Quad) | Centrifugal (Quad) | Centrifugal (Quad / Multi) |
| **Operational Speed Range** | 1 - 7 m/s | 1 - 9 m/s | 1 - 10 m/s | 1 - 12 m/s |
| **Operational Height Range** | 1.5 - 5 m | 1.5 - 6 m | 1.5 - 7 m | 2.0 - 8 m |

*Note: All parameters will be verified against official public specifications, technical teardowns, and authorized measurement logs.*

---

## 8. Missing Engineering Information
- Exact 3D CAD geometries of propeller blade sectional profiles (NACA sections, twist, and chord distributions).
- Detailed motor torque-RPM curves under dynamic electrical loads.
- Precise internal tank baffling geometry affecting sloshing and instantaneous center of gravity.
- Proprietary ESC (Electronic Speed Controller) mixing algorithms during asymmetrical flight maneuvers.
- *Mitigation:* Reconstruct accurate parametric blade boundary representations and actuator disk/line momentum distributions anchored in empirical thrust and power measurements.

---

## 9. Governing Equations
### Fluid Phase (RANS - Incompressible Navier-Stokes)
$$\frac{\partial \bar{u}_i}{\partial x_i} = 0$$
$$\frac{\partial (\rho \bar{u}_i)}{\partial t} + \frac{\partial (\rho \bar{u}_i \bar{u}_j)}{\partial x_j} = -\frac{\partial \bar{p}}{\partial x_i} + \frac{\partial}{\partial x_j} \left[ \mu \left( \frac{\partial \bar{u}_i}{\partial x_j} + \frac{\partial \bar{u}_j}{\partial x_i} \right) - \rho \overline{u_i' u_j'} \right] + S_{body,i} + S_{droplet,i}$$

### Turbulence Closure ($k-\omega$ SST model)
$$\frac{\partial (\rho k)}{\partial t} + \frac{\partial (\rho \bar{u}_j k)}{\partial x_j} = \tilde{P}_k - \beta^* \rho k \omega + \frac{\partial}{\partial x_j} \left[ \left(\mu + \sigma_k \mu_t\right) \frac{\partial k}{\partial x_j} \right]$$
$$\frac{\partial (\rho \omega)}{\partial t} + \frac{\partial (\rho \bar{u}_j \omega)}{\partial x_j} = \gamma \frac{\rho}{\mu_t} \tilde{P}_k - \beta \rho \omega^2 + \frac{\partial}{\partial x_j} \left[ \left(\mu + \sigma_\omega \mu_t\right) \frac{\partial \omega}{\partial x_j} \right] + 2(1 - F_1) \frac{\rho \sigma_{\omega2}}{\omega} \frac{\partial k}{\partial x_j} \frac{\partial \omega}{\partial x_j}$$

### Discrete Phase (Lagrangian Particle Tracking)
$$m_p \frac{d \vec{u}_p}{dt} = \vec{F}_d + \vec{F}_g + \vec{F}_{turb}$$
$$\vec{F}_d = \frac{1}{2} C_d \rho_f A_p |\vec{u}_f - \vec{u}_p| (\vec{u}_f - \vec{u}_p)$$
$$\text{Particle Reynolds Number: } Re_p = \frac{\rho_f d_p |\vec{u}_f - \vec{u}_p|}{\mu_f}$$
$$\text{Stokes Number: } St = \frac{\rho_p d_p^2 U_{ref}}{18 \mu_f L_{ref}}$$

---

## 10. CFD Approach Comparison
| Fidelity Level | Method | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Level 0** | Momentum Theory / Blade Element Momentum (BEM) | Extremely fast, analytical | No 3D wake detail, no airframe interaction | **Initial order-of-magnitude checks only** |
| **Level 1** | Actuator Disk (AD) | Low computational cost, captures bulk downwash | Smears azimuthal velocities, misses tip vortices | **DOE screening & rapid sensitivity runs** |
| **Level 2** | Actuator Line Method (ALM) | Captures tip vortices and blade interaction | Requires high grid resolution near rotor discs | **Secondary dynamic flow analysis** |
| **Level 3** | Multiple Reference Frame (MRF) | Steady-state rotor rotation, good wake representation | Approximates blade-to-frame interaction | **Primary aerodynamics & droplet baseline** |
| **Level 4** | Sliding Mesh (Transient) | Full unsteady blade-vortex interaction | Extremely computationally expensive | **Validation of select high-fidelity cases** |

---

## 11. Recommended Initial Solver
- **Primary CFD Engine:** OpenFOAM (v11 or later / OpenFOAM-v2312) utilizing `pisoFoam` / `interFoam` / `sprayFoam` or custom Eulerian-Lagrangian solvers (`icoReactingMultiphaseInterFoam` / `dpmFoam`).
- **Meshing:** `snappyHexMesh` with automated multi-region refinement boxes around rotor planes, wake paths, and ground deposition planes.

---

## 12. Turbulence Model Recommendation
- **SST $k-\omega$ (Shear Stress Transport):** Selected as the baseline turbulence model due to its superior performance in adverse pressure gradients, wall-bounded boundary layers, and free shear flows typical of rotor slipstreams.
- **Realizable $k-\varepsilon$:** Evaluated comparatively for large open-domain wake dissipation.

---

## 13. Droplet Model Recommendation
- **Discrete Phase Model (DPM) / Lagrangian Particle Tracking (LPT):** Fully coupled momentum exchange between continuous fluid and discrete droplets.
- **Droplet Size Distribution:** Rosin-Rammler distribution parameterized by $D_{V0.1}, D_{V0.5}$ (VMD), and $D_{V0.9}$, accounting for atomization spectra from centrifugal nozzles. Evaporation modeled via standard Spalding mass transfer number if relative humidity deviates.

---

## 14. Coupling Recommendation
- **Two-Way Coupling:** Mandatory. Droplet mass flow rates and momentum transfer significantly impact local air velocity fields in dense agricultural spray plumes, particularly directly beneath high-capacity multirotors (T70P, T100).

---

## 15. Validation Experiment
- **Aerodynamic Validation:** Sonic anemometry array or multi-hole pressure probes mounted on a ground gantry measuring $v_z(x,y)$ beneath hovering/moving Agras platforms.
- **Spray Deposition Validation:** Fluorescent tracer (e.g., Pyranine or Rhodamine B) recovered from horizontal collector cards and analyzed via spectrofluorometry, complemented by water-sensitive papers for droplet sizing ($D_{V0.5}$) across a transverse sampling line ($0.25\text{ m}$ spacing over a $15\text{ m}$ span).

---

## 16. DOE Proposal
- **Method:** Latin Hypercube Sampling (LHS) and Sobol sequences for space-filling parameter exploration.
- **Design Variables & Ranges:**
  - Forward Speed ($V_\infty$): $2.0 \text{ to } 10.0 \text{ m/s}$
  - Flight Altitude ($H$): $1.5 \text{ to } 6.0 \text{ m}$
  - Median Droplet Size ($D_{V0.5}$): $150 \text{ to } 400\ \mu\text{m}$
  - Tank Load Fraction ($m/m_{max}$): $0.1, 0.25, 0.5, 0.75, 1.0$
  - Atomizer Configuration: 2 nozzles (outboard) vs. 4 nozzles (staggered front/rear).

---

## 17. Surrogate Proposal
- **Algorithm:** Gaussian Process Regression (GPR) with Matern 5/2 kernel, coupled with Active Learning / Adaptive Sampling based on epistemic prediction variance ($\sigma^2_{GPR}$).
- **Outputs:** Transverse deposition profile $D(x)$, Coefficient of Variation ($CV$), Effective Swath Width ($W_{eff}$), and Peak Deposition Location.

---

## 18. Data Schema
Structured JSON / HDF5 / SQLite database schema storing:
- Metadata (`drone_model`, `mesh_id`, `solver_version`, `timestamp`)
- Operating Conditions (`speed`, `height`, `droplet_spectrum`, `payload_fraction`, `atomizer_config`)
- Spatial Fields (`velocity_vector_field`, `pressure`, `TKE`)
- Deposition Outputs (`D_x_y`, `D_transverse`, `CV`, `effective_swath`, `recommended_spacing`, `uncertainty_bounds`).

---

## 19. Computational Estimate
- **Mesh Size:** ~15 to 30 million polyhedral/hexahedral cells per case.
- **Compute Resources:** High-Performance Computing (HPC) cluster nodes (AMD EPYC / Intel Xeon with 64+ cores per simulation case). Estimated total core-hours: ~150,000 core-hours across DOE and mesh convergence studies.

---

## 20. Scientific Risks
- Excessive numerical diffusion in actuator disk models masking tip vortex breakdown.
- Convergence difficulties in transient sliding mesh simulations under high forward speed conditions.
- Scale-up inaccuracies when extrapolating droplet evaporation and secondary breakup phenomena.

---

## 21. Publication Risks
- Proprietary restrictions on exact DJI proprietary blade geometries (mitigated by parametric airfoil reconstruction validated against thrust curves).
- Reviewer skepticism regarding wind tunnel vs. open-field atmospheric turbulence discrepancies.

---

## 22. Conflict-of-Interest Considerations
- One investigator maintains affiliation with an agricultural drone commercialization entity. 
- *Mitigation:* Full transparency declaration, reliance on public empirical data, third-party validation benchmarks, and complete open-source code/data repositories to ensure scientific objectivity.

---

## 23. Recommended Order of Execution
1. **PHASE_00 & PHASE_01:** Literature review, technical specification matrices, data classification.
2. **PHASE_02:** Geometry reconstruction & CAD preparation (T25P baseline).
3. **PHASE_03:** Baseline CFD (Actuator Disk & MRF) for T25P airflow verification.
4. **PHASE_04:** Experimental validation of air velocity fields ($V_z$).
5. **PHASE_05 & PHASE_06:** Particle tracking introduction and spray deposition validation.
6. **PHASE_07 & PHASE_08:** DOE execution across all 4 platforms and dataset compilation.
7. **PHASE_09 & PHASE_10:** Surrogate modeling, active learning, and operational optimization.
8. **PHASE_11:** Manuscript drafting and open data release.

---

## 24. Explicit Stop/Go Criteria for Next Phase
- **Gate 1 Criteria:** All physical dimensions, rotor diameters, mass limits, and operating envelopes for T25P, T55, T70P, and T100 must be fully audited and classified (`public`, `measured`, `inferred`, `estimated`) with documented references before approving transition to `PHASE_02_GEOMETRY`.
