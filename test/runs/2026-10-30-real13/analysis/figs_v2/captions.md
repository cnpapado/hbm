# Draft captions (rev.csv, v2)

## ratios_same

STV of a 2D baseline divided by that of HBM with the same kind of T source and a layout fixed for all circuits, per circuit and as the geometric mean (GMean): Planar-2D against HBM-Ded, both with factories, and 2D-Cult (one cultivation patch per data qubit) against HBM-Cult-Ded, both with cultivation patches. Ded: one T source per data qubit. Above the dashed line (1), HBM has the lower STV. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## split

The STV ratios of Fig. ratios_same split into their two factors: physical qubits (x) and rounds (y; timesteps × code distance) of the 2D baseline divided by those of HBM, one marker per circuit. Circles: Planar-2D over HBM-Ded (factories); squares: 2D-Cult (one cultivation patch per data qubit) over HBM-Cult-Ded (cultivation). Beyond 1 on an axis, HBM uses fewer qubits or rounds; above the dashed curve (x·y = 1), HBM has the lower STV. Markers that coincide share one label. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## split_s2

As Fig. split, for HBM's S2 layout: physical qubits (x) and rounds (y; timesteps × code distance) of the 2D baseline divided by those of HBM, one marker per circuit. Circles: Planar-2D over HBM-S2 (factories); squares: 2D-Cult (one cultivation patch per data qubit) over HBM-Cult-S2 (cultivation). Beyond 1 on an axis, HBM uses fewer qubits or rounds; above the dashed curve (x·y = 1), HBM has the lower STV. Markers that coincide share one label. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## heatmap

STV of every configuration (columns) on every circuit (rows), divided by the lowest STV on that circuit; the boxed cell (1.00) is the circuit's best configuration. Columns: the 2D baselines (2D-Cult with one or half a cultivation patch per data qubit, Planar-2D), HBM with factories on top and HBM-Cult with cultivation patches on top, each with one source per data qubit (Ded) or one source shared by 2 to 16 data qubits (S2-S16). Row labels give the circuit's T count. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## sharing

STV of a 2D baseline divided by that of HBM with the same kind of T source, against HBM's sharing ratio (Ded: one T source per data qubit; S2-S16: one source per 2 to 16 data qubits): Planar-2D over HBM, both with factories (solid), and 2D-Cult (one patch per data qubit) over HBM-Cult, both with cultivation patches (dashed). Lines: geometric mean over the circuits; bands: range. The two lines use different baselines, so their heights are not comparable with each other. Above the dashed line (1), HBM has the lower STV; log scale.

## sources

STV of a 2D baseline divided by that of HBM with the same kind of T source, against the number of T sources in HBM over that in the baseline, one panel per circuit: Planar-2D against HBM, both with factories (solid), and 2D-Cult (one cultivation patch per data qubit) against HBM-Cult, both with cultivation patches (dashed). Markers give HBM's layout, from one source per data qubit (Ded) to one per 16 (S16). Above the dashed line (1), HBM has the lower STV; on the dotted line both use the same number of sources; log-log. The two lines use different baselines, so their heights are not comparable with each other. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## sources_vs_2dcult

STV of 2D-Cult (one cultivation patch per data qubit) divided by that of HBM with factories on top, against the number of factories in HBM over the number of cultivation patches in 2D-Cult, one panel per circuit. The two sides use different T sources: factories are always ready, while a cultivation patch recharges after each T state. Markers give HBM's layout, from one factory per data qubit (Ded) to one per 16 (S16). Above the dashed line (1), HBM has the lower STV; on the dotted line both use the same number of T sources; log-log. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17). *: the circuit's T count requires the slower cultivation grade (R = 360 rounds).

## spacetime_ising-66

Space and time of representative configurations on Ising-66. Left: physical qubits, split into data tiles, other tiles (routing and unused) and T-state sources (factories or cultivation patches). Right: runtime in rounds (log scale); the dashed line is the stall-free runtime (ideal depth × d). Labels: the configuration's STV relative to the lowest on this circuit and its code distance.

## tradeoff_ising-66

Physical qubits against runtime in rounds for every configuration on Ising-66 (log-log). Lines join the layouts of a family (2D-Cult: one and half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S16). Grey lines join points of equal STV, ten times apart; points further to the lower left have lower STV. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17).

## spacetime_ising-34

Space and time of representative configurations on Ising-34. Left: physical qubits, split into data tiles, other tiles (routing and unused) and T-state sources (factories or cultivation patches). Right: runtime in rounds (log scale); the dashed line is the stall-free runtime (ideal depth × d). Labels: the configuration's STV relative to the lowest on this circuit and its code distance.

## tradeoff_ising-34

Physical qubits against runtime in rounds for every configuration on Ising-34 (log-log). Lines join the layouts of a family (2D-Cult: one and half a cultivation patch per data qubit; HBM and HBM-Cult: Ded to S16). Grey lines join points of equal STV, ten times apart; points further to the lower left have lower STV. All runs at the smallest odd code distance that meets the program-error target, chosen per run (d = 11-17).
