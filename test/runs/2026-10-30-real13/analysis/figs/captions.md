# Draft captions (numbers from rev.csv)

## ratios

**HBM cuts space-time volume by 4.06× over 2D cultivation (2.7× at R = 60, 12.3× on the * circuits) and 1.23× over the planar factory layout (geometric means); with cultivation on both sides HBM-Cult still saves 1.19×.** Each bar is the baseline's STV over HBM's, each side at its best layout (higher is better; log scale). HBM vs Planar-2D ranges 0.96–1.40×. *: the T count forces the slower R = 360 cultivation grade.

## heatmap

**Dedicated HBM with factories on top has the lowest space-time volume on most circuits (best: HBM-Ded on 9, HBM-S2 on 1, Planar-2D on 1 of 11); sharing a source among more data qubits raises it, most with cultivation (up to 318×).** Each cell is a configuration's STV over the best on its circuit (boxed: 1). †: misses the 1% error target at d = 13 (its STV is a lower bound). *: R = 360 cultivation.

## sharing

**Sharing a T source does not pay at these T densities: HBM goes from 1.23× (Ded) to 0.16× (S16) of the best 2D baseline's STV, HBM-Cult from 0.36× to 0.019×.** Lines: geometric mean over the 11 circuits of the best 2D baseline's STV over HBM's (higher is better); bands: range.

## scaling

**HBM has the lowest STV on 10 of 11 circuits; both cultivation families jump once the T count forces the slow grade (*).** Best configuration of each family against the number of logical qubits (log STV). Hollow: misses the error target.

## spacetime_ising-66

**Ising-66*: HBM-Ded spends 71% of its qubits on factories but runs within 1.00× of the stall-free time; cultivation layouts are small but wait for recharge (27× the stall-free time for 2D-Cult).** Left: physical qubits by role. Right: rounds (log); dashed: stall-free (ideal depth × d); labels: STV over the best configuration. †: misses the error target.

## tradeoff_ising-66

**Ising-66*: HBM trades qubits for time along the lowest-STV contours, while sharing cultivation patches saves almost no qubits and costs many rounds.** Each point is a configuration (log-log); grey lines: equal STV, 10× apart (lower left is better); lines join the sharing ratios Ded–S16. Hollow: misses the error target.

## spacetime_ising-34

**Ising-34: HBM-Ded spends 70% of its qubits on factories but runs within 1.00× of the stall-free time; cultivation layouts are small but wait for recharge (6× the stall-free time for 2D-Cult).** Left: physical qubits by role. Right: rounds (log); dashed: stall-free (ideal depth × d); labels: STV over the best configuration. †: misses the error target.

## tradeoff_ising-34

**Ising-34: HBM trades qubits for time along the lowest-STV contours, while sharing cultivation patches saves almost no qubits and costs many rounds.** Each point is a configuration (log-log); grey lines: equal STV, 10× apart (lower left is better); lines join the sharing ratios Ded–S16. Hollow: misses the error target.
