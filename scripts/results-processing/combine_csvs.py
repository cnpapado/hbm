#!/usr/bin/env python3

import pandas as pd
import sys

def combine_csv(files, output_file="combined.csv"):
    if not files:
        print("No input files provided.")
        return

    combined_df = None

    for file in files:
        df = pd.read_csv(file)
        if combined_df is None:
            combined_df = df
        else:
            # Merge on 'Benchmark', keeping all columns
            combined_df = pd.merge(combined_df, df, on='Benchmark', how='outer')

    combined_df.to_csv(output_file, index=False)
    print(f"Combined CSV saved to {output_file}")

if __name__ == "__main__":
    # CSV files are passed as command line arguments
    input_files = sys.argv[1:]
    combine_csv(input_files)
