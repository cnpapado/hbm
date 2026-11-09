# runs/real1 analysis

11 one-step circuits (Ising n10-n66, QED-C Heisenberg n16-n64), d = 13, 4 h per run.

- `rev_all.csv`: every finished run (`scripts/revision/analyze.py runs/real1/outs/real`).
  `rev.csv`: the paper's 8 configurations only. `table_*`: `stv_table.py` on each.
- `occupancy.{png,csv}`: data qubits vs padded data slots per circuit
  (`scripts/revision/draw_occupancy.py`).
- `figs_bottom/`, `figs_top/`: the paper's Figs. 13-15 (`split`, `split_s2`, `sources`),
  drawn with `plot_results.py --set v2` from `revision/fair-baselines` on `rev_bottom.csv` /
  `rev_top.csv`. Those two CSVs relabel runs into the figure's slots:
  - `rev_bottom.csv`: HBM-S{2,4,8,16} (factories) are the `D3-s{k}-fact-bottom` runs and
    HBM-Cult-S2 is `D3-rows-bottom`.
  - `rev_top.csv`: HBM-S{k} are the top-routed `D3-s{k}-fact` runs and HBM-Cult-S2 is
    `D3-rows`.
  Cultivation S4-S16 are not defined, so their markers are missing (and the `sharing`
  figure is not drawn). `D3-ancilla-bottom` and `D3-full-bottom` are not in the figures.

## Dense cultivation layouts (all bottom-first except `D3-rows`)

STV relative to HBM-Ded cultivation (`D3-k1`), from `rev_all.csv`; lower is better.
`rows` = patches on the data rows, `ancilla` = above every routing tile, `full` = whole
upper layer (a patch above a data qubit serves only that qubit). heis n49/n64 and ising
n66 use R360; the rest R60.

| circuit | D2-tight | rows (top) | rows (bottom) | ancilla | full |
|---|---|---|---|---|---|
| ising n10 | 1.42 | 0.37 | 0.27 | 0.29 | 0.32 |
| ising n13 | 1.33 | 0.48 | 0.37 | 0.30 | 0.33 |
| heis n16  | 1.35 | 0.60 | 0.48 | 0.36 | 0.35 |
| ising n16 | 1.37 | 0.59 | 0.46 | 0.33 | 0.33 |
| heis n20  | 1.46 | 0.52 | 0.39 | 0.32 | 0.33 |
| heis n25  | 1.47 | 0.61 | 0.49 | 0.37 | 0.36 |
| ising n26 | 1.18 | 0.39 | 0.31 | 0.29 | 0.32 |
| ising n34 | 1.19 | 0.50 | 0.41 | 0.32 | 0.33 |
| heis n49  | 1.34 | 0.64 | 0.51 | 0.36 | 0.33 |
| heis n64  | 1.33 | 0.67 | 0.52 | 0.37 | 0.33 |
| ising n66 | 1.25 | 0.47 | 0.36 | 0.24 | 0.23 |
