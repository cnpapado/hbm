# Draft captions (rev.csv)

## ratios

Space-time volume (STV) of each baseline divided by that of HBM, per circuit and as the geometric mean (GMean), with each side at its best layout: HBM (factories on top) against 2D cultivation (2D-Cult), HBM-Cult (cultivation on top) against 2D-Cult, and HBM against the planar factory layout (Planar-2D). Above the dashed line (1), HBM has the lower STV; log scale. All runs at code distance d = 13. *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## heatmap

STV of every configuration (columns) on every circuit (rows), divided by the lowest STV on that circuit; the boxed cell (1.00) is the circuit's best configuration. Columns: the 2D baselines (2D-Cult with one or half a cultivation patch per data qubit, Planar-2D), HBM with factories on top and HBM-Cult with cultivation patches on top, each with one source per data qubit (Ded) or one source shared by 2 to 16 data qubits (S2-S16). Row labels give the circuit's T count. †: the run exceeds the program-error target at d = 13. *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## sharing

STV of the best 2D baseline divided by that of HBM, against HBM's sharing ratio (Ded: one T source per data qubit; S2-S16: one source per 2 to 16 data qubits), for HBM with factories (solid) and HBM-Cult with cultivation patches (dashed). Lines: geometric mean over the circuits; bands: range. Above the dashed line (1), HBM has the lower STV; log scale.

## scaling

Lowest STV of each family (2D-Cult, Planar-2D, HBM, HBM-Cult) against the number of logical qubits, for the Ising (left) and Heisenberg (right) circuits; log scale. Hollow markers: the run exceeds the program-error target at d = 13.

## spacetime_ising-66

Space and time of representative configurations on Ising-66. Left: physical qubits, split into data tiles, other tiles (routing and unused) and T-state sources (factories or cultivation patches). Right: runtime in rounds (log scale); the dashed line is the stall-free runtime (ideal depth × d). Labels: the configuration's STV relative to the lowest on this circuit. †: the run exceeds the program-error target at d = 13.

## tradeoff_ising-66

Physical qubits against runtime in rounds for every configuration on Ising-66 (log-log). Lines join the layouts of a family (2D-Cult: one and half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S16). Grey lines join points of equal STV, ten times apart; points further to the lower left have lower STV. Hollow markers: the run exceeds the program-error target at d = 13.

## spacetime_ising-34

Space and time of representative configurations on Ising-34. Left: physical qubits, split into data tiles, other tiles (routing and unused) and T-state sources (factories or cultivation patches). Right: runtime in rounds (log scale); the dashed line is the stall-free runtime (ideal depth × d). Labels: the configuration's STV relative to the lowest on this circuit. †: the run exceeds the program-error target at d = 13.

## tradeoff_ising-34

Physical qubits against runtime in rounds for every configuration on Ising-34 (log-log). Lines join the layouts of a family (2D-Cult: one and half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S16). Grey lines join points of equal STV, ten times apart; points further to the lower left have lower STV. Hollow markers: the run exceeds the program-error target at d = 13.
