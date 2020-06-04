#!/usr/bin/python
# updateJBrowsefiles.py

import sys
import os


def main(argv):
    # get new GFF file and unzip it
    os.system(
        'wget -P /var/www/html/jbrowse/yeast_reference https://downloads.yeastgenome.org/latest/saccharomyces_cerevisiae.gff.gz')

    os.system(
        'gunzip -f /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff.gz')

    # run scripts

    os.system('/var/www/html/jbrowse/bin/flatfile-to-json.pl --gff /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff --trackLabel S288C --trackType CanvasFeatures')
    os.system('/var/www/html/jbrowse/bin/flatfile-to-json.pl --gff /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff --trackLabel All\ Annotated\ Sequence\ Features --trackType CanvasFeatures --noSubfeatures --type ARS, blocked_reading_frame, centromere, chromosome, gene, long_terminal_repeat, LTR_retrotransposon, mating_type_region, ncRNA_gene, origin_of_replication, pseudogene, rRNA_gene, silent_mating_type_cassette_array, snoRNA_gene, snRNA_gene, telomerase_RNA_gene, telomere, transposable_element_gene, tRNA_gene')
    os.system('/var/www/html/jbrowse/bin/flatfile-to-json.pl --gff /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff --trackLabel Protein-Coding-Genes --trackType CanvasFeatures --type CDS, five_prime_UTR_intron, gene, intein_encoding_region, mRNA, plus_1_translational_frameshift, transposable_element_gene')
    os.system('/var/www/html/jbrowse/bin/flatfile-to-json.pl --gff /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff --trackLabel Non-Coding-RNA-Genes --trackType CanvasFeatures --type cRNA_gene, rRNA_gene, snoRNA_gene, snRNA_gene, tRNA_gene')
    os.system('/var/www/html/jbrowse/bin/flatfile-to-json.pl --gff /var/www/html/jbrowse/yeast_reference/saccharomyces_cerevisiae.gff --trackLabel Subfeatures --trackType CanvasFeatures --type ARS_consensus_sequence, CDS, centromere_DNA_Element_I, centromere_DNA_Element_II, centromere_DNA_Element_III, external_transcribed_spacer_region, five_prime_UTR_intron, intein_encoding_region, internal_transcribed_spacer_region, intron, noncoding_exon, non_transcribed_region, plus_1_translational_frameshift, telomeric_repeat, W_region, X_element, X_element_combinatorial_repeat, X_region, Y_prime_element, Z1_region, Z2_region')

    # copy new tracks over

    os.system('cp -r /var/www/html/jbrowse/yeast_reference/data/tracks/Protein-Coding-Genes/* /var/www/html/jbrowse/data/tracks/Protein-Coding-Genes/')
    os.system(
        'cp -r /var/www/html/jbrowse/yeast_reference/data/tracks/Subfeatures/* /var/www/html/jbrowse/data/tracks/Subfeatures/')
    os.system(
        'cp -r /var/www/html/jbrowse/yeast_reference/data/tracks/S288C/* /var/www/html/jbrowse/data/tracks/S288C/')
    os.system('cp -r /var/www/html/jbrowse/yeast_reference/data/tracks/All\ Annotated\ Sequence\ Features/* /var/www/html/jbrowse/data/tracks/All\ Annotated\ Sequence\ Features/')
    os.system('cp -r /var/www/html/jbrowse/yeast_reference/data/tracks/Non-Coding-RNA-Genes/* /var/www/html/jbrowse/data/tracks/Non-coding-RNA-Genes/')


if __name__ == "__main__":
    main(sys.argv[1:])
