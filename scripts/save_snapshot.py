#!/usr/bin/env python3
"""Simple helper to copy raw SAP export files into test_data/raw and record a run manifest.

Usage examples:
  python scripts/save_snapshot.py --prdpl3 "/path/to/PRDPL3.csv" --mrp_rec "/path/MRP_REC.csv" --powerquery "/path/powerquery_output.xlsx"
  python scripts/save_snapshot.py --run-id 20260804_143223 --copy-all-dir "/path/to/raw_folder"

The script copies files into test_data/raw and writes runs/<run_id>/manifest.json with recorded source paths.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_RAW = os.path.join(ROOT, 'test_data', 'raw')
RUNS = os.path.join(ROOT, 'runs')


def ensure_dirs():
    os.makedirs(TEST_RAW, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)


def copy_if_provided(src_path, dest_dir):
    if not src_path:
        return None
    if not os.path.exists(src_path):
        print(f"Warning: source not found: {src_path}")
        return None
    basename = os.path.basename(src_path)
    dst = os.path.join(dest_dir, basename)
    shutil.copy2(src_path, dst)
    return dst


def create_manifest(run_id, entries, as_of_date=None):
    run_dir = os.path.join(RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)
    manifest_path = os.path.join(run_dir, 'manifest.json')
    manifest = {
        'run_id': run_id,
        'started_at': datetime.now().isoformat(),
        'created_by': os.getenv('USER') or os.getenv('USERNAME') or 'unknown',
        'status': 'completed',
        'as_of_date': as_of_date,
        'sources': entries,
        'row_counts': {k + '_raw': 0 for k in ['prdpl3','mrp_rec','mrp_doh','mb5t']},
        'notes': 'Snapshot captured by scripts/save_snapshot.py'
    }
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f"Wrote manifest: {manifest_path}")
    return manifest_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', help='Run id (default: timestamp)')
    parser.add_argument('--prdpl3')
    parser.add_argument('--mrp_rec')
    parser.add_argument('--mrp_doh')
    parser.add_argument('--mb5t')
    parser.add_argument('--powerquery', help='Power Query/current export to save into test_data/expected')
    parser.add_argument('--copy-all-dir', help='Copy all files from a directory into test_data/raw')
    parser.add_argument('--as-of-date', help='As-of date to record in manifest (YYYY-MM-DD)')
    args = parser.parse_args()

    ensure_dirs()
    run_id = args.run_id or datetime.now().strftime('%Y%m%d_%H%M%S')

    copied = {}
    if args.copy_all_dir:
        if not os.path.isdir(args.copy_all_dir):
            print('copy-all-dir is not a directory')
            sys.exit(1)
        for fname in os.listdir(args.copy_all_dir):
            src = os.path.join(args.copy_all_dir, fname)
            if os.path.isfile(src):
                dst = copy_if_provided(src, TEST_RAW)
                if dst:
                    copied[fname] = dst
    else:
        copied['prdpl3'] = copy_if_provided(args.prdpl3, TEST_RAW)
        copied['mrp_rec'] = copy_if_provided(args.mrp_rec, TEST_RAW)
        copied['mrp_doh'] = copy_if_provided(args.mrp_doh, TEST_RAW)
        copied['mb5t'] = copy_if_provided(args.mb5t, TEST_RAW)
        copied['powerquery_output'] = copy_if_provided(args.powerquery, os.path.join(ROOT, 'test_data', 'expected'))

    # normalize None values to null in manifest
    entries = {k: (v if v else None) for k, v in copied.items()}
    create_manifest(run_id, entries, as_of_date=args.as_of_date)


if __name__ == '__main__':
    main()
