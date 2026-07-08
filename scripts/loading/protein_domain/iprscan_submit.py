#!/usr/bin/env python3
"""
Submit protein sequences to EBI InterProScan REST API and retrieve results.

EBI InterProScan API documentation:
https://www.ebi.ac.uk/seqdb/confluence/display/JDSAT/InterProScan+5+Help+and+Documentation

Usage:
    python iprscan_submit.py proteins.fasta --output results/
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# EBI InterProScan REST API endpoints
BASE_URL = "https://www.ebi.ac.uk/Tools/services/rest/iprscan5"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('iprscan_submit.log')
    ]
)
logger = logging.getLogger(__name__)


def clean_sequence(seq: str) -> str:
    """
    Clean a protein sequence for InterProScan submission.

    The EBI InterProScan REST service only accepts standard amino-acid
    characters. SGD ORF translations carry a trailing '*' stop codon, and
    a handful of dubious ORFs contain internal stops. Strip a single
    trailing stop and replace any remaining internal stops with 'X'
    (unknown residue), which InterProScan accepts.
    """
    seq = seq.strip().upper()
    if seq.endswith('*'):
        seq = seq[:-1]
    if '*' in seq:
        seq = seq.replace('*', 'X')
    return seq


def parse_fasta(fasta_file: str) -> dict[str, str]:
    """Parse FASTA file and return dict of {header: cleaned sequence}."""
    sequences = {}
    current_header = None
    current_seq = []

    with open(fasta_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if current_header:
                    sequences[current_header] = clean_sequence(''.join(current_seq))
                current_header = line[1:].split()[0]  # Use first word as ID
                current_seq = []
            else:
                current_seq.append(line)

        # Don't forget the last sequence
        if current_header:
            sequences[current_header] = clean_sequence(''.join(current_seq))

    return sequences


def submit_job(sequence: str, seq_id: str, email: str) -> Optional[str]:
    """
    Submit a single sequence to InterProScan.

    Returns job ID if successful, None otherwise.
    """
    url = f"{BASE_URL}/run"

    data = {
        'email': email,
        'title': seq_id,
        'sequence': sequence,
        'goterms': 'true',
        'pathways': 'true',
    }

    try:
        response = requests.post(url, data=data, timeout=60)
        if response.status_code == 200:
            job_id = response.text.strip()
            logger.info(f"Submitted {seq_id}: job_id={job_id}")
            return job_id
        else:
            logger.error(f"Failed to submit {seq_id}: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {seq_id}: {e}")
        return None


def check_status(job_id: str) -> str:
    """Check the status of a submitted job."""
    url = f"{BASE_URL}/status/{job_id}"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text.strip()
        else:
            return "ERROR"
    except requests.exceptions.RequestException:
        return "ERROR"


def get_result(job_id: str, result_type: str = "tsv") -> Optional[str]:
    """
    Retrieve results for a completed job.

    result_type options: tsv, json, xml, gff, svg, htmltarball, sequence
    """
    url = f"{BASE_URL}/result/{job_id}/{result_type}"

    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to get results for {job_id}: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving results for {job_id}: {e}")
        return None


def wait_for_job(job_id: str, max_wait: int = 3600, poll_interval: int = 30) -> str:
    """
    Wait for a job to complete.

    Returns final status: FINISHED, FAILURE, ERROR, or TIMEOUT
    """
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status = check_status(job_id)

        if status == "FINISHED":
            return "FINISHED"
        elif status in ("FAILURE", "ERROR", "NOT_FOUND"):
            return status

        # Still running, wait and poll again
        time.sleep(poll_interval)

    return "TIMEOUT"


def load_progress(progress_file: str) -> dict:
    """Load progress from checkpoint file."""
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'submitted': {}, 'completed': [], 'failed': []}


def save_progress(progress_file: str, progress: dict):
    """Save progress to checkpoint file."""
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Submit protein sequences to EBI InterProScan REST API'
    )
    parser.add_argument('fasta', help='Input FASTA file')
    parser.add_argument('--output', '-o', default='iprscan_results',
                        help='Output directory for results (default: iprscan_results)')
    parser.add_argument('--email', '-e', required=True,
                        help='Your email address (required by EBI)')
    parser.add_argument('--batch-size', '-b', type=int, default=25,
                        help='Number of jobs to submit before waiting (default: 25)')
    parser.add_argument('--poll-interval', '-p', type=int, default=30,
                        help='Seconds between status checks (default: 30)')
    parser.add_argument('--max-concurrent', '-m', type=int, default=25,
                        help='Maximum concurrent jobs (default: 25)')
    parser.add_argument('--format', '-f', default='tsv',
                        choices=['tsv', 'json', 'xml', 'gff'],
                        help='Output format (default: tsv)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from previous run')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Progress file for resuming
    progress_file = output_dir / 'progress.json'

    # Load sequences
    logger.info(f"Loading sequences from {args.fasta}")
    sequences = parse_fasta(args.fasta)
    logger.info(f"Loaded {len(sequences)} sequences")

    # Load or initialize progress
    if args.resume:
        progress = load_progress(str(progress_file))
        logger.info(f"Resuming: {len(progress['completed'])} completed, "
                    f"{len(progress['failed'])} failed")
    else:
        progress = {'submitted': {}, 'completed': [], 'failed': []}

    # Filter out already completed sequences
    remaining = {k: v for k, v in sequences.items()
                 if k not in progress['completed'] and k not in progress['failed']}
    logger.info(f"{len(remaining)} sequences remaining to process")

    if not remaining:
        logger.info("All sequences already processed!")
        return

    # Process sequences in batches
    seq_items = list(remaining.items())
    active_jobs = {}  # job_id -> seq_id

    # Add any previously submitted but not completed jobs
    for seq_id, job_id in progress.get('submitted', {}).items():
        if seq_id not in progress['completed'] and seq_id not in progress['failed']:
            active_jobs[job_id] = seq_id

    idx = 0
    while idx < len(seq_items) or active_jobs:
        # Submit new jobs if we have capacity
        while idx < len(seq_items) and len(active_jobs) < args.max_concurrent:
            seq_id, sequence = seq_items[idx]

            # Skip if already submitted
            if seq_id in progress.get('submitted', {}):
                idx += 1
                continue

            job_id = submit_job(sequence, seq_id, args.email)

            if job_id:
                active_jobs[job_id] = seq_id
                progress['submitted'][seq_id] = job_id
                save_progress(str(progress_file), progress)

            idx += 1

            # Small delay between submissions to be nice to the API
            time.sleep(1)

        # Check status of active jobs
        completed_jobs = []
        for job_id, seq_id in active_jobs.items():
            status = check_status(job_id)
            logger.debug(f"Job {job_id} ({seq_id}): {status}")

            if status == "FINISHED":
                # Download results
                result = get_result(job_id, args.format)
                # A None return means an HTTP/transport error (real failure).
                # An empty string is a valid result with no domain hits -- many
                # dubious/short ORFs have none -- so still record it as completed.
                if result is not None:
                    result_file = output_dir / f"{seq_id}.{args.format}"
                    with open(result_file, 'w') as f:
                        f.write(result)
                    if result.strip():
                        logger.info(f"Saved results for {seq_id}")
                    else:
                        logger.info(f"No domain hits for {seq_id} (empty result)")
                    progress['completed'].append(seq_id)
                else:
                    logger.error(f"No result retrieved for {seq_id} (HTTP error)")
                    progress['failed'].append(seq_id)

                completed_jobs.append(job_id)
                save_progress(str(progress_file), progress)

            elif status in ("FAILURE", "ERROR", "NOT_FOUND"):
                logger.error(f"Job failed for {seq_id}: {status}")
                progress['failed'].append(seq_id)
                completed_jobs.append(job_id)
                save_progress(str(progress_file), progress)

        # Remove completed jobs from active list
        for job_id in completed_jobs:
            del active_jobs[job_id]

        # Wait before next poll if we have active jobs
        if active_jobs:
            logger.info(f"Waiting... {len(active_jobs)} jobs active, "
                        f"{len(progress['completed'])} completed, "
                        f"{idx}/{len(seq_items)} submitted")
            time.sleep(args.poll_interval)

    # Final summary
    logger.info("=" * 50)
    logger.info("InterProScan submission complete!")
    logger.info(f"Total sequences: {len(sequences)}")
    logger.info(f"Completed: {len(progress['completed'])}")
    logger.info(f"Failed: {len(progress['failed'])}")
    logger.info(f"Results saved to: {output_dir}")

    # Combine all TSV results into one file
    if args.format == 'tsv':
        combined_file = output_dir / 'all_results.tsv'
        with open(combined_file, 'w') as outf:
            for result_file in output_dir.glob('*.tsv'):
                if result_file.name == 'all_results.tsv':
                    continue
                with open(result_file, 'r') as inf:
                    outf.write(inf.read())
        logger.info(f"Combined results saved to: {combined_file}")


if __name__ == '__main__':
    main()
