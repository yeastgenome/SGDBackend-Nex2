import os
import subprocess
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from Bio import Phylo

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_clustal_omega(input_file, output_prefix):
    """Run Clustal Omega to generate alignment and tree files in Clustal format."""
    aligned_file = f"{output_prefix}_aligned.aln"  # Use .aln extension for Clustal format
    tree_file = f"{output_prefix}.dnd"
    
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

def generate_tree_image(tree_file, image_file, gene_name):
    """Generate a tree image from the tree file using Bio.Phylo and matplotlib."""
    try:
        if not os.path.exists(tree_file):
            logging.error(f"Tree file {tree_file} not found for {gene_name}, skipping...")
            return
        
        logging.info(f"Generating tree image from {tree_file}")
        
        # Read the Newick tree with Bio.Phylo
        tree = Phylo.read(tree_file, "newick")
        
        # Create a plot
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Collect the positions of the clades for annotation
        def get_clade_positions(tree, branch_length=0.0, positions=None, max_height=1):
            if positions is None:
                positions = {}
            if tree.is_terminal():
                positions[tree] = (branch_length, max_height)
                max_height += 1
            else:
                for clade in tree:
                    max_height = get_clade_positions(clade, branch_length + (clade.branch_length or 0), positions, max_height)
                positions[tree] = (branch_length, (positions[tree.clades[0]][1] + positions[tree.clades[-1]][1]) / 2)
            return max_height
        
        positions = {}
        get_clade_positions(tree.root, positions=positions)
        
        # Draw the branches
        for clade in tree.find_clades(order='level'):
            if clade.is_terminal():
                x = positions[clade][0]
                y = positions[clade][1]
                ax.text(x, y, clade.name, verticalalignment='center', fontsize=10, color='red' if clade.name == f"{gene_name}_S288C" else 'black')
            else:
                for child in clade:
                    x1, y1 = positions[clade]
                    x2, y2 = positions[child]
                    ax.plot([x1, x2], [y1, y2], color='black')
                    ax.plot([x2, x2], [y2, y2], color='black')
        
        # Remove x and y labels
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Remove default labels and box
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Add 'SGD' label to the bottom left corner
        ax.text(-0.1, -0.1, 'SGD', color='black', fontsize=12, va='bottom', ha='left', transform=ax.transAxes)
        
        # Add image generated date to bottom right corner
        current_date = datetime.now().strftime("%Y-%m-%d")
        ax.text(1.1, -0.1, current_date, color='black', fontsize=12, va='bottom', ha='right', transform=ax.transAxes)
        
        # Save the plot to a file
        plt.savefig(image_file, format='png', dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        logging.info(f"Tree image saved to {image_file}")
    except Exception as e:
        logging.error(f"Error generating tree image: {e}")

def process_gene_sequences(input_dir, output_dir):
    """Process all gene sequence files in the input directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for file_name in os.listdir(input_dir):
        if file_name.endswith("_protein.seq"):
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
            generate_tree_image(tree_file, image_file, gene_name)
            logging.info(f"Generated alignment and tree image for {gene_name}")
            logging.info(f"Alignment file: {aligned_file}")
            logging.info(f"Tree image file: {image_file}")
            
            # Remove the temporary input file
            os.remove(temp_input_file)

# Example usage
input_dir = "data/protein_seq/"
output_dir = "data/protein_align/"
process_gene_sequences(input_dir, output_dir)
