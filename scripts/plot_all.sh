#!/bin/bash

python plot_results.py --metric speedup
python plot_results.py --metric speedup --normalize_qubits
python plot_results.py --metric speedup --normalize_magic_states

python plot_results.py --metric footprint
python plot_results.py --metric footprint --normalize_qubits
python plot_results.py --metric footprint --normalize_magic_states

python plot_results.py --metric tdp
python plot_results.py --metric tdp --normalize_qubits
python plot_results.py --metric tdp --normalize_magic_states
