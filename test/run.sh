#!/bin/bash

export HBM_CONFIG="no_hbm"
wisq bench_ordered_10t.qasm -op test_NO_HBM.out --mode scmr

export HBM_CONFIG="shared_none"
wisq bench_ordered_10t.qasm -op test_ARCH_A.out --mode scmr


python print_timesteps.py test_NO_HBM.out
echo ""
python print_timesteps.py test_ARCH_A.out