import os
import subprocess
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from Bio import Phylo
from Bio.Phylo.BaseTree import Clade, Tree

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

seqtype = 'protein'
key_name_color = 'red'
other_name_color = 'blue'

def generate_tree_image(tree_file, image_file, gene_name):
    """Generate a tree image from the tree file using Bio.Phylo and matplotlib."""

    try:
        if not os.path.exists(tree_file):
            logging.error(f"Tree file {tree_file} not found for {gene_name}, skipping...")
            return

        logging.info(f"Generating tree image from {tree_file}")

        # Read the Newick tree with Bio.Phylo
        tree = Phylo.read(tree_file, "newick")

        # Create a plot with increased figure size
        fig, ax = plt.subplots(figsize=(12, 10))

        # Get a list of all clades in the tree
        clades = tree.get_terminals() + tree.get_nonterminals()

        # Sort the clades based on their names
        label_colors = {}
        for clade in tree.find_clades():
            if clade.name == f"{gene_name}_S288C":
                label_colors[clade.name] = key_name_color
            else:
                label_colors[clade.name] = other_name_color

        # Draw the tree with the label colors
        Phylo.draw(tree, do_show=False, axes=ax, label_colors=label_colors)

        # Add 'SGD' label to the bottom left corner
        ax.text(-0.1, -0.1, 'SGD', color='black', fontsize=12, va='bottom', ha='left', transform=ax.transAxes)

        # Add image generated date to bottom right corner
        current_date = datetime.now().strftime("%Y-%m-%d")
        ax.text(1.1, -0.1, current_date, color='black', fontsize=12, va='bottom', ha='right', transform=ax.transAxes)

        # Suppress the x- and y-labels
        ax.set_xlabel('')
        ax.set_ylabel('')

        # Suppress the x- and y-tick marks and numbers
        ax.set_xticks([])
        ax.set_yticks([])

        # Adjust layout to make more space for the tree
        fig.tight_layout()

        # Expand the tree toward the right side by adjusting the x-axis limits
        x_min, x_max = ax.get_xlim()
        ax.set_xlim([x_min, x_max * 2])  # Adjust the multiplier to control the expansion

        # Save the plot to a file
        plt.savefig(image_file, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)

        logging.info(f"Tree image saved to {image_file}")

    except Exception as e:
        logging.error(f"Error generating tree image: {e}")



def run_clustal_omega(input_file, output_prefix):
    """Run Clustal Omega to generate alignment and tree files in Clustal format."""
    aligned_file = f"{output_prefix}.align"
    tree_file = f"{output_prefix}.dnd"
    if seqtype == 'dna':
        aligned_file = f"{output_prefix}_dna.align"
        tree_file = f"{output_prefix}_dna.dnd"
    
    cmd = [
        "clustalo",
        "-i", input_file,
        "-o", aligned_file,
        "--guidetree-out", tree_file,
        "--force",
        "--outfmt", "clu"  # Ensure Clustal output format
    ]
    logging.info(f"Running Clustal Omega with command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"Clustal Omega failed with error: {result.stderr}")
    else:
        logging.info(f"Clustal Omega output: {result.stdout}")
    
    # Check if files were generated
    if not os.path.exists(aligned_file):
        logging.error(f"Aligned file {aligned_file} not found after running Clustal Omega.")
    if not os.path.exists(tree_file):
        logging.error(f"Tree file {tree_file} not found after running Clustal Omega.")
    
    return aligned_file, tree_file



def process_gene_sequences(input_dir, output_dir):
    """Process all gene sequence files in the input directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for file_name in os.listdir(input_dir):
        if file_name.endswith(f"_{seqtype}.seq"):
            gene_name = file_name.split('_')[0]
            key_gene = f"{gene_name}_S288C"
            input_file = os.path.join(input_dir, file_name)
            output_prefix = os.path.join(output_dir, gene_name)
            
            # Read input sequences and ensure key gene is present
            with open(input_file, 'r') as f:
                sequences = f.read().strip().split('>')
                sequences = [seq for seq in sequences if seq.strip() != '']
            
            key_gene_present = False
            unique_sequences = set()
            
            for seq in sequences:
                header, sequence = seq.split('\n', 1)
                sequence = sequence.replace('\n', '')  # Remove newline characters within sequences
                if key_gene in header:
                    key_gene_present = True
                unique_sequences.add(f">{header}\n{sequence}\n")
            
            if not key_gene_present:
                logging.warning(f"Key gene {key_gene} not found in {file_name}")
                continue
            
            if len(unique_sequences) < 2:
                logging.warning(f"File {file_name} contains less than 2 unique sequences after filtering, skipping...")
                continue
            
            # Write unique sequences to a temporary file
            temp_input_file = input_file + ".tmp"
            with open(temp_input_file, 'w') as f:
                f.writelines(unique_sequences)
            
            aligned_file, tree_file = run_clustal_omega(temp_input_file, output_prefix)
            
            # Verify alignment file content
            if not os.path.exists(aligned_file):
                logging.error(f"Aligned file {aligned_file} not found for {gene_name}, skipping...")
                os.remove(temp_input_file)
                continue
            
            with open(aligned_file) as f:
                alignment_content = f.read()
                logging.info(f"Content of the alignment file {aligned_file}:\n{alignment_content}")
                if alignment_content == "":
                    logging.error(f"Alignment failed for {gene_name}")
                    os.remove(temp_input_file)
                    continue
            
            # Verify tree file content
            if not os.path.exists(tree_file):
                logging.error(f"Tree file {tree_file} not found for {gene_name}, skipping...")
                os.remove(temp_input_file)
                continue
            
            with open(tree_file) as f:
                tree_content = f.read()
                logging.info(f"Content of the tree file {tree_file}:\n{tree_content}")
                if tree_content == "":
                    logging.error(f"Tree generation failed for {gene_name}")
                    os.remove(temp_input_file)
                    continue
            
            # Generate tree image
            image_file = f"{output_prefix}.png"
            if seqtype == 'dna':
                image_file = f"{output_prefix}_{seqtype}.png"
            generate_tree_image(tree_file, image_file, gene_name)
            logging.info(f"Generated alignment and tree image for {gene_name}")
            logging.info(f"Alignment file: {aligned_file}")
            logging.info(f"Tree image file: {image_file}")
            
            # Remove the temporary input file
            os.remove(temp_input_file)

# Example usage
input_dir = f"data/{seqtype}_seq/"
output_dir = f"data/{seqtype}_align/"
process_gene_sequences(input_dir, output_dir)
