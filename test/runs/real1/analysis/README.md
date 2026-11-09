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
