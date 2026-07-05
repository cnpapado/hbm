#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define the array of code distances
DISTANCES=(3 5 7 9 11)

# Generate 15 logarithmically spaced error rates from 1e-3 to 1e-1 using Python
ERROR_RATES=$(python -c "import numpy as np; print(' '.join(map(str, np.logspace(-3, -1, 15))))")

# Constant parameters
RECORDS=100000

echo "=========================================================="
echo "Starting decoder bench batch generation"
echo "Distances: ${DISTANCES[*]}"
echo "Error rates generated: 15 steps from 0.001 to 0.1"
echo "=========================================================="

# Loop over each distance
for d in "${DISTANCES[@]}"; do
    
    # Loop over each error rate
    for p in $ERROR_RATES; do
        
        echo "[$(date +'%H:%M:%S')] Running generator: d=$d, p=$p"
        
        # Execute the python script
        python decoder_bench/generator.py \
            --code=ls \
            --basis=z \
            --noise=circuit \
            -d "$d" \
            -p "$p" \
            --records="$RECORDS"
            
    done
done

echo "=========================================================="
echo "Batch execution completed successfully!"
echo "=========================================================="