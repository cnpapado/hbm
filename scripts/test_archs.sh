#!/bin/bash
# set -e 

HBM_CONFIGS=(
    "no_hbm"
    "shared_none"
    "shared_none-anchilla_perimeter"
    "shared_2-route_bottom"
    "shared_2-route_bottom-anchilla_perimeter"
    "shared_2-route_upper"
    "shared_2-route_upper-anchilla_perimeter"
    "shared_4-route_bottom"
    "shared_4-route_bottom-anchilla_perimeter"
    "shared_4-route_upper" 
    "shared_4-route_upper-anchilla_perimeter"
)

ARCHS=(
    "square_sparse_layout"
    "compact_layout"
)

QUBITS_LIST=(2 4 9 16 25 36 49 64 81 100 121 144 169)

for arch in "${ARCHS[@]}"; do
    
    for qubits in "${QUBITS_LIST[@]}"; do
        # Create temporary QASM file with one line
        file=$(mktemp --suffix=".qasm")
        {
            echo "OPENQASM 2.0;"
            echo "include \"qelib1.inc\";"
            echo "qreg q[$qubits];"
            for ((i=0; i<qubits; i++)); do
                echo "t q[$i];"
            done
        } > "$file"
    
        echo "running $file"
        for config in "${HBM_CONFIGS[@]}"; do
            export HBM_CONFIG="$config"
            wisq "$file" -op hbm.out --mode scmr -arch "$arch" -va "${HBM_CONFIG}-${arch}-${qubits}.png"
        done
    done
done
