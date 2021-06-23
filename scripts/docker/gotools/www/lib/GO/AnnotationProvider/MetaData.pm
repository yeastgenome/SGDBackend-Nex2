package GO::AnnotationProvider::MetaData;

##############################################################################
# FILE: MetaData.pm
# DATE CREATED: August 2004
# AUTHOR: Linda McMahan <lmcmahan@genomics.princeton.edu>
#
##############################################################################

##############################################################################
# POD (PLAIN OLD DOCUMENTATION)
##############################################################################

=pod

=head1 NAME

GO::AnnotationProvider::MetaData - Provide attributes and methods to deal with gene annotation files available at GO ftp site.

=head1 SYNOPSIS

=over 4

  use GO::AnnotationProvider::AnnotationParser;
  use go::AnnotationProvider::MetaData;


   my $metaData = GO::AnnotationProvider::MetaData->new();

   # Get this organism's total annotated gene number from its gene association file
   my $annotionFilePath = '/usr/local/go/lib/GO/gene_association.sgd';
   my $annotationParser = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotionFilePath);
   my @databaseIds = $annotationParser->allDatabaseIds();
   my $annotateGeneNum = scalar(@databaseIds);

   my $annotionFile = 'gene_association.sgd';

   # Call these mutator methods to set values of these attributes for this organism
   $metaData->setANNOTATION_FILE($file, $annotationFile);
   $metaData->setANNOTATE_GENE_NUM($annotateGeneNum, $annotationFile);
   $metaData->setESTIMATE_GENE_NUM($annotationFile);

   # Call these accessor methods to return values of these attributes for this organism
   my ($organismGeneUrl) = $metaData->getGENE_URL($annotationFile);
   my ($organismCommonName) = $metaData->getCOMMON_NAME($annotationFile);
   my ($ogranismScientificName) = $metaData->getORGANISM($annotationFile);
   my ($organismDatabaseName) = $metaData->getORGANISM_DB_NAME($annotationFile);
   my ($organismDatabaseUrl) = $metaData->getORGANISM_DB_URL($annotationFile);

   print "Organism Gene Url: ", $organismGeneUrl, "\n",
         "Organism Common Name: ", $organismCommonName, "\n",
         "Organism Scientific Name: ", $ogranismScientificName, "\n",
         "Organism Database Name: ", $organismDatabaseName, "\n",
         "Organism Database URL: ", $organismDatabaseUrl, "\n";

   # Call this accessor method to return a reference of all attributes for this organism
   my ($organismInfoHashRef) = $metaData->getOrganismInfo($annotationFile);
   # @organismInfoArray contains references to the info about all the organisms
   my @organismsInfoArray; 
   push(@organismsInfoArray, $organismInfoHashRef);

   # Call this method to create an html table of gene association file for these files
   my $filepath = "/Genomics/curtal/www/go/html/GOTermMapper/MetaData.html";
   $metaData->createGeneAsscTable(\@organismsInfoArray, $filepath);

   # Call this method to get the values and labels of gene annotation files.  These returned values and 
   # labels can then be used to create cgi script's pull-down menu of gene annotation files 
   my ($geneAssValuesArrayRef, $geneAssLabelsHashRef) = $metaData->geneAnnotationFilesMenu;

   # Call this method to get the estimate total gene number for this organism
   my ($estimateGeneNum) = $metaData->organismEstimateTotalGeneNum($annotionFile);

   # Call this method to get the gene url for this organism   
   my $opt_u = 'http://genome-www4.stanford.edu/cgi-bin/SGD/locus.pl?locus=';
   my ($geneUrl) = $metaData->organismGeneUrl($annotationFile, $opt_u);

   # Call this method to check if the gene annotation file exists for this organism
   my ($organismFileExist) = $metaData->organismFileExist($annotationFile);

=back

=cut

##############################################################################


use strict;
use warnings;
use vars '$AUTOLOAD'; #keep 'use strict' happy
use Carp;

use CGI qw/:all :html3/;

use vars qw (@ISA @EXPORT_OK %dir);  #keep 'use strict' happy 
use Exporter;
@ISA = ('Exporter');
@EXPORT_OK = qw(createGeneAsscTable geneAnnotationFilesMenu geneAnnotationSlimFilesMenu organismEstimateTotalGeneNum organismGeneUrl organismFileExist);


my $DEBUG = 0; #debugging variable; set to 1 for printed feedback (i.e. to print debug statements)


###############################################################################
## ATTRIBUTES OF ORGANISMS
###############################################################################
## we annotate gene product to the organism rather than to the
## annotation file, on the premise that there can be multiple
## annotations files per organism (sources, custom, etc,)
##

my %organismEstimateTotalGeneNum = (
#                                    'Arabidopsis thaliana' => 52816,
                                    'Bacillus anthracis' => 5507,
				    'Bos taurus' => 37225,
                                    'Caenorhabditis elegans' => 22246,
#                                    'Candida albicans' => 6840,
                                    'Coxiella burnetii' => 2095,
                                    'Danio rerio' => 22409,
                                    'Dictyostelium discoideum' => 12098,
                                    'Drosophila melanogaster'  => 16085,
				    'Escherichia coli' => 7187,
				    'Gallus gallus' => 30837,
                                    'Geobacter sulfurreducens PCA' => 3533,
#                                    'Homo sapiens' => 23531,
#                                    'Mus musculus' => 33884,
                                    'Oryza sativa' => 41521,
				    'Plasmodium falciparum' => 5400,
                                    'Pseudomonas syringae' => 5763,
#                                    'Rattus norvegicus' => 23751,
                                    'Saccharomyces cerevisiae' => 7166,
                                    'Shewanella oneidensis' => 4843,
                                    'Trypanosoma brucei' => 708,
                                    'Vibrio cholerae' => 3885,  
				    );


###############################################################################
## ATTRIBUTES OF GO GENE ANNOTATION FILES
###############################################################################
## associations files have the following STATIC attributes (defined):
#
#
#    GENE_URL - a template URL to link to for more inforamtion on a gene
#    COMMON_NAME (Note, this should probably be an attribute of the organism; oh well...)
#    ORGANISM - Genus and species (must match keys of organismEstimateTotalGeneNum, above.)
#    ORGANISM_DB_NAME  - annotations authority or file source
#    ORGANISM_DB_URL - URL of authority
#    DEFAULT_GENE_URL - a sample link
#    README_URL - README file from authority located at GO site, http://www.geneontology.org/gene-associations/readme/
#    IDENTIFIER_2 - type of identifier at column 2 of association file (e.g. 'systematic name', 'gene name', 'gene symbol')
#    IDENTIFIER_2_EXAMPLE - example identifier at column 2 of association file
#    IDENTIFIER_3 - type of identifier at column 3 of association file
#    IDENTIFIER_3_EXAMPLE  - example identifier at column 3 of association file
#    IDENTIFIER_11 - type of identifier at column 11 of association file
#    IDENTIFIER_11_EXAMPLE - example identifier at column 11 of association file
#    SAMPLE_GENE_LIST - sample list of identifiers, usable by the tools
#    CONVERSION_TOOL  - {a reference to an hash of label => url}, suggested to assist in identifier conversion
#    ANNOTATION_FILE => the full name of the annotation file
#
## the following attributes are only set is the gene assocaition files
## are usable by the web applications, GOTermFinder, GOTermMapper
#    MENU_LABEL       => the menu label the the GOTermFinder will display
#    SLIM_MENU_LABEL  => the menu label the the GOTermMapper will display
#
## the following attribute is set AFTER the file as been parsed
#    ANNOTATE_GENE_NUM - the number of annotated gene products in the association file
#
## and the following attribute may be set if it is defined in % organismEstimateTotalGeneNum, above
#    ESTIMATE_GENE_NUM - the estimated number of gene products in the organism, both annotated and unannotated
#

my $uniprot = {'UniProt Batch Retrieval' => 'http://www.uniprot.org/batch/',
	       'CNIO Clone/Gene ID converter' => 'http://idconverter.bioinfo.cnio.es/'};

my %_annotationFiles = (
			GeneDB_Lmajor => {
			    GENE_URL => undef,
			    COMMON_NAME => 'Skin parasite',
			    ORGANISM => 'Leishmania major',
			    ORGANISM_DB_NAME => 'L. major GeneDB',
			    ORGANISM_DB_URL => 'http://www.genedb.org/Homepage/Lmajor',
			    DEFAULT_GENE_URL => '',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/GeneDB_Lmajor.README',
			    IDENTIFIER_2 => 'Systematic_ID',
			    IDENTIFIER_3 => 'Systematic_ID',
			    IDENTIFIER_11 => '',
			    IDENTIFIER_2_EXAMPLE => 'LM5.39',
			    IDENTIFIER_3_EXAMPLE => 'L6071.09',
			    IDENTIFIER_11_EXAMPLE => '',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/geneDB_Lmajor.txt',
			    ANNOTATION_FILE => 'gene_association.GeneDB_Lmajor',
			    MENU_LABEL => 'GeneDB_Lmajor',
			    SLIM_MENU_LABEL => 'GeneDB_Lmajor (Generic GO slim)'
			    },
			GeneDB_Pfalciparum => {
			    GENE_URL => 'http://www.genedb.org/genedb/Search?organism=malaria&name=',
			    COMMON_NAME => 'Malaria parasite',
			    ORGANISM => 'Plasmodium falciparum',
			    ORGANISM_DB_NAME => 'P. falciparum GeneDB',
			    ORGANISM_DB_URL => 'http://www.genedb.org/Homepage/Pfalciparum',
			    DEFAULT_GENE_URL => 'http://www.genedb.org/genedb/Search?organism=malaria&name'.'=PFF1145c',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/GeneDB_Pfalciparum.README',
			    IDENTIFIER_2 => 'Systematic Name',
			    IDENTIFIER_3 => 'Systematic Name',
			    IDENTIFIER_11 => '',
			    IDENTIFIER_2_EXAMPLE => 'PFF1145c',
			    IDENTIFIER_3_EXAMPLE => 'MAL6P1.191',
			    IDENTIFIER_11_EXAMPLE => '',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/geneDB_pfalciparum.txt',
			    ANNOTATION_FILE => 'gene_association.GeneDB_Pfalciparum',
			    MENU_LABEL  => 'GeneDB_Pfalciparum',
			    SLIM_MENU_LABEL  => 'GeneDB_Pfalciparum (Generic GO slim)'
			    },
			# GeneDB_Spombe => {
			#     GENE_URL => 'http://www.genedb.org/genedb/Search?organism=pombe&name=',
			#     COMMON_NAME => 'Yeast',
			#     ORGANISM => 'Schizosaccharomyces pombe',
			#     ORGANISM_DB_NAME => 'S. pombe GeneDB',
			#     ORGANISM_DB_URL => 'http://www.genedb.org/genedb/pombe/',
			#     DEFAULT_GENE_URL => 'http://www.genedb.org/genedb/Search?organism'.'=pombe&name'.'=clp1',
			#     README_URL => 'http://www.geneontology.org/gene-associations/readme/GeneDB_Spombe.README',
			#     IDENTIFIER_2 => 'Systematic Name',
			#     IDENTIFIER_3 => 'Gene Name',
			#     IDENTIFIER_11 => 'Gene Synonym',
			#     IDENTIFIER_2_EXAMPLE => 'SPAC1782.09c',
			#     IDENTIFIER_3_EXAMPLE => 'clp1',
			#     IDENTIFIER_11_EXAMPLE => 'flp1',
			#     SAMPLE_GENE_LIST => '/sampleGeneFiles/geneDB_spombe.txt',
			#     ANNOTATION_FILE => 'gene_association.GeneDB_Spombe',
			#     MENU_LABEL  => 'GeneDB_Spombe',
			#     SLIM_MENU_LABEL  => 'GeneDB_Spombe (S. pombe GO slim) (Process only)'
			#     },
			# GeneDB_Spombe_generic => {
			#     ANNOTATION_FILE => 'gene_association.GeneDB_Spombe_generic',
			#     SLIM_MENU_LABEL  => 'GeneDB_Spombe (Generic GO slim)'
			# },
			pombase => {
#			    GENE_URL => 'http://www.genedb.org/genedb/Search?organism=pombe&name=',
			    GENE_URL => 'http://www.pombase.org/search/ensembl/',
			    COMMON_NAME => 'Yeast',
			    ORGANISM => 'Schizosaccharomyces pombe',
#			    ORGANISM_DB_NAME => 'S. pombe GeneDB',
			    ORGANISM_DB_NAME => 'PomBase',
#			    ORGANISM_DB_URL => 'http://www.genedb.org/genedb/pombe/',
			    ORGANISM_DB_URL => 'http://www.pombase.org/',
			    DEFAULT_GENE_URL => 'http://www.pombase.org/spombe/result/clp1',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/pombase.README',
			    IDENTIFIER_2 => 'Systematic Name',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Gene Synonym',
			    IDENTIFIER_2_EXAMPLE => 'SPAC1782.09c',
			    IDENTIFIER_3_EXAMPLE => 'clp1',
			    IDENTIFIER_11_EXAMPLE => 'flp1',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/pombase.txt',
			    ANNOTATION_FILE => 'gene_association.pombase',
			    MENU_LABEL  => 'PomBase',
			    SLIM_MENU_LABEL  => 'PomBase (S. pombe GO slim) (Process only)'
			    },
			GeneDB_Spombe_generic => {
			    ANNOTATION_FILE => 'gene_association.pombase_generic',
			    SLIM_MENU_LABEL  => 'PomBase (Generic GO slim)'
			},
			GeneDB_Tbrucei => {
			    GENE_URL => 'http://www.genedb.org/genedb/Search?organism=tryp&name=',
			    COMMON_NAME => 'Trypanosome',
			    ORGANISM => 'Tryanosoma brucei',
			    ORGANISM_DB_NAME => 'T. brucei GeneDB',
			    ORGANISM_DB_URL => 'http://www.genedb.org/Homepage/Tbruceibrucei927',
			    DEFAULT_GENE_URL => 'http://www.genedb.org/genedb/Search?organism'.'=tryp&name'.'=Tb927.2.380',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/GeneDB_Tbrucei.README',
			    IDENTIFIER_2 => 'Systematic Name',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Gene Synonym',
			    IDENTIFIER_2_EXAMPLE => 'Tb927.2.380',
			    IDENTIFIER_3_EXAMPLE => 'RHS2',
			    IDENTIFIER_11_EXAMPLE => '3B10.145',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/geneDB_Tbrucei.txt',
			    ANNOTATION_FILE => 'gene_association.GeneDB_Tbrucei',
			    MENU_LABEL  => 'GeneDB_Tbrucei',
			    SLIM_MENU_LABEL  => 'GeneDB_Tbrucei (Generic GO slim)'
			    },
			# GeneDB_tsetse => {
			#     GENE_URL => 'http://www.genedb.org/genedb/Search?organism=glossina&name=',
			#     COMMON_NAME => 'Tsetse fly',
			#     ORGANISM => 'Glossina morsitans',
			#     ORGANISM_DB_NAME => 'G. morsitans GeneDB',
			#     ORGANISM_DB_URL => 'http://www.genedb.org/genedb/glossina/index.jsp',
			#     DEFAULT_GENE_URL => 'http://www.genedb.org/genedb/Search?organism='.'glossina&name'.'=Gmm-1621',
			#     README_URL => 'http://www.geneontology.org/gene-associations/readme/GeneDB_Tsetse.README',
			#     IDENTIFIER_2 => 'Systematic Name',
			#     IDENTIFIER_3 => '',
			#     IDENTIFIER_11 => '',
			#     IDENTIFIER_2_EXAMPLE => 'Gmm-1621',
			#     IDENTIFIER_3_EXAMPLE => '',
			#     IDENTIFIER_11_EXAMPLE => '',
			#     SAMPLE_GENE_LIST => '/sampleGeneFiles/geneDB_tsetse.txt',
			#     ANNOTATION_FILE => 'gene_association.GeneDB_tsetse',
			#     MENU_LABEL  => 'GeneDB_tsetse',
			#     SLIM_MENU_LABEL  => 'GeneDB_tsetse (Generic GO slim)'
			#     },
			cgd => {
			    GENE_URL => 'http://www.candidagenome.org/cgi-bin/locus.pl?locus=',
			    COMMON_NAME => 'Candida',
			    ORGANISM => 'Candida albicans',
			    ORGANISM_DB_NAME => 'CGD',
			    ORGANISM_DB_URL => 'http://www.candidagenome.org/',
			    DEFAULT_GENE_URL => 'http://www.candidagenome.org/cgi-bin/locus.pl?locus='.'=act1',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/cgd.README',
			    IDENTIFIER_2 => 'CGD_ID',
			    IDENTIFIER_3 => 'Standard Name',
			    IDENTIFIER_11 => 'Systematic name',
			    IDENTIFIER_2_EXAMPLE => 'CAL0005516',
			    IDENTIFIER_3_EXAMPLE => 'AAF1',
			    IDENTIFIER_11_EXAMPLE => 'orf19.7436',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/cgd.txt',
			    ANNOTATION_FILE => 'gene_association.cgd',
			    MENU_LABEL  => 'CGD (Candida - C. albicans)',
			    SLIM_MENU_LABEL  => 'CGD - Candida (Generic GO slim)'
			    },
			dictyBase => {
			    GENE_URL => 'http://dictybase.org/db/cgi-bin/dictyBase/locus.pl?locus=',
			    COMMON_NAME => 'Slime mold',
			    ORGANISM => 'Dictyostelium discoideum',
			    ORGANISM_DB_NAME => 'DictyBase',
			    ORGANISM_DB_URL => 'http://dictybase.org/',
			    DEFAULT_GENE_URL => 'http://dictybase.org/db/cgi-bin/dictyBase/locus.pl?locus'.'=yakA',
			    README_URL => '',
			    IDENTIFIER_2 => 'DictyBase_ID',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Alias',
			    IDENTIFIER_2_EXAMPLE => 'DDB_G0267450',
			    IDENTIFIER_3_EXAMPLE => 'yakA',
			    IDENTIFIER_11_EXAMPLE => 'dagB',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/dictyBase.txt',
			    ANNOTATION_FILE => 'gene_association.dictyBase',
			    MENU_LABEL  => 'DictyBase (Slime mold - D. discoideum)',
			    SLIM_MENU_LABEL  => 'DictyBase (Generic GO slim)'
			    },
#			ddb => {
#			    GENE_URL => 'http://dictybase.org/db/cgi-bin/dictyBase/locus.pl?locus=',
#			    COMMON_NAME => 'Slime mold',
#			    ORGANISM => 'Dictyostelium discoideum',
#			    ORGANISM_DB_NAME => 'DictyBase',
#			    ORGANISM_DB_URL => 'http://dictybase.org/',
#			    DEFAULT_GENE_URL => 'http://dictybase.org/db/cgi-bin/dictyBase/locus.pl?locus'.'=yakA',
#			    README_URL => '',
#			    IDENTIFIER_2 => 'DictyBase_ID',
#			    IDENTIFIER_3 => 'Gene Name',
#			    IDENTIFIER_11 => 'Alias',
#			    IDENTIFIER_2_EXAMPLE => 'DDB0191191',
#			    IDENTIFIER_3_EXAMPLE => 'yakA',
#			    IDENTIFIER_11_EXAMPLE => 'dagB',
#			    SAMPLE_GENE_LIST => '/sampleGeneFiles/ddb.txt',
#			    ANNOTATION_FILE => 'gene_association.ddb',
#			    MENU_LABEL  => 'DictyBase (Slime mold - D. discoideum)',
#			    SLIM_MENU_LABEL  => 'DictyBase (Generic GO slim)'
#			    },
			fb => {
			    GENE_URL => 'http://flybase.bio.indiana.edu/.bin/fbidq.html?',
			    COMMON_NAME => 'Fruit fly',
			    ORGANISM => 'Drosophila melanogaster',
			    ORGANISM_DB_NAME => 'FlyBase',
			    ORGANISM_DB_URL => 'http://flybase.bio.indiana.edu/',
			    DEFAULT_GENE_URL => 'http://flybase.bio.indiana.edu/.bin/fbidq.html?FBgn0013749',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/fb.README',
			    IDENTIFIER_2 => 'FlyBase_ID',
			    IDENTIFIER_3 => 'Gene Symbol',
			    IDENTIFIER_11 => 'Gene Synonym',
			    IDENTIFIER_2_EXAMPLE => 'FBgn0013749',
			    IDENTIFIER_3_EXAMPLE => 'Arf102F',
			    IDENTIFIER_11_EXAMPLE => 'ARF2',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/fb.txt',
			    CONVERSION_TOOL => '',     
			    ANNOTATION_FILE => 'gene_association.fb',  
			    MENU_LABEL  => 'FlyBase (Fruit fly - D. melanogaster)',
			    SLIM_MENU_LABEL  => 'FlyBase (Generic GO slim)'
			    },
			goa_arabidopsis => {
			    ORGANISM => 'Arabidopsis thaliana',
			    #  subsumed by TAIR file
			},
			goa_chicken => {
			    ORGANISM => 'Gallus gallus',
			    COMMON_NAME => 'Chicken',
			    ORGANISM_DB_NAME => 'GOA @EBI',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_chicken.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_chicken',
			    MENU_LABEL  => 'goa_chicken'
			    },
			goa_cow => {
			    ORGANISM => 'Bos taurus',
			    COMMON_NAME => 'Cow',
			    ORGANISM_DB_NAME => 'GOA @EBI',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_cow.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_cow',
			    MENU_LABEL  => 'goa_cow'
			    },
			goa_Ecoli => {
			    ORGANISM => 'Escherichia coli',
			    COMMON_NAME => 'Bacterium coli',
			    ORGANISM_DB_NAME => 'GOA @EBI',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_Ecoli',
			    MENU_LABEL  => 'goa_ecoli'
			    },
			goa_human => {
			    GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene=',
			    COMMON_NAME => 'Human',
			    ORGANISM => 'Homo sapiens',
			    ORGANISM_DB_NAME => 'GOA @EBI',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    DEFAULT_GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene='.'ENSG00000039600&db'.'=core',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index',
			    IDENTIFIER_2_EXAMPLE => 'O94993',
			    IDENTIFIER_3_EXAMPLE => 'SX30_HUMAN',
			    IDENTIFIER_11_EXAMPLE => 'IPI00016680',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_human.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_human',
			    MENU_LABEL  => 'goa_human',
			    SLIM_MENU_LABEL  => 'goa_human (GOA GO slim)'
			    },
			goa_human_generic => {ANNOTATION_FILE => 'gene_association.goa_human_generic',
					      SLIM_MENU_LABEL  => 'goa_human (Generic GO slim)'
					      },
 			goa_human_hgnc => {
			    # augmented goa_human
#			    GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene=',
			    GENE_URL => 'http://www.genenames.org/data/hgnc_data.php?hgnc_id=',
			    COMMON_NAME => 'Human',
			    ORGANISM => 'Homo sapiens',
			    ORGANISM_DB_NAME => 'GOA @EBI + XREFs',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    DEFAULT_GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene='.'ENSG00000039600&db'.'=core',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index with additional crossreferenced gene symbols',
			    IDENTIFIER_2_EXAMPLE => 'O94993',
			    IDENTIFIER_3_EXAMPLE => 'SX30_HUMAN',
			    IDENTIFIER_11_EXAMPLE => 'IPI00016680|SOX30',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_human_hgnc.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_human_hgnc',
			    MENU_LABEL  => 'goa_human_hgnc',
			    SLIM_MENU_LABEL  => 'goa_human_hgnc (GOA GO slim)'
			    },
			goa_human_hgnc_generic => {ANNOTATION_FILE => 'gene_association.goa_human_hgnc_generic',
						   SLIM_MENU_LABEL  => 'goa_human_hgnc (Generic GO slim)'
					      },
 			goa_human_ensembl => {
			    # augmented goa_human
			    GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene=',
			    COMMON_NAME => 'Human',
			    ORGANISM => 'Homo sapiens',
			    ORGANISM_DB_NAME => 'GOA @EBI + Ensembl',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    DEFAULT_GENE_URL => 'http://www.ensembl.org/Homo_sapiens/geneview?gene='.'ENSG00000039600&db'.'=core',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index with additional crossreferenced gene symbols',
			    IDENTIFIER_2_EXAMPLE => 'O94993',
			    IDENTIFIER_3_EXAMPLE => 'SX30_HUMAN',
			    IDENTIFIER_11_EXAMPLE => 'IPI00016680|SOX30',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_human_ensembl.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_human_ensembl',
			    MENU_LABEL  => 'goa_human_ensembl',
			    SLIM_MENU_LABEL  => 'goa_human_ensembl (GOA GO slim)'
			    },
			goa_human_ensembl_generic => {ANNOTATION_FILE => 'gene_association.goa_human_ensembl_generic',
						      SLIM_MENU_LABEL  => 'goa_human_ensembl (Generic GO slim)'
                            },
			#     # subsumed by RGD?
			#     GENE_URL => 'http://www.ensembl.org/Mus_musculus/geneview?gene=',
			#     COMMON_NAME => 'Mouse',
			#     ORGANISM => 'Mus musculus',
			#     ORGANISM_DB_NAME => 'GOA @EBI',
			#     ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			#     DEFAULT_GENE_URL => 'http://www.ensembl.org/Mus_musculus/geneview?gene='.'ENSMUSG00000055141&db'.'=core',
			#     README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			#     IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			#     IDENTIFIER_3 => 'UniProt_Id (or Ensembl_ID)',
			#     IDENTIFIER_11 => 'International Protein Index',
			#     IDENTIFIER_2_EXAMPLE => 'P07628',
			#     IDENTIFIER_3_EXAMPLE => 'KLK8_MOUSE',
			#     IDENTIFIER_11_EXAMPLE => 'IPI00130801',
			#     SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_mouse.txt',
			#     CONVERSION_TOOL => $uniprot,
			#     ANNOTATION_FILE => 'gene_association.goa_mouse',
			#     },
#			goa_mouse_generic => {ANNOTATION_FILE => 'gene_association.goa_mouse_generic',
#					      SLIM_MENU_LABEL  => 'goa_mouse (Generic GO slim)'
#					      },
# 			goa_pdb => {
# # UNUSED???
# 			    GENE_URL => 'http://www.rcsb.org/pdb/cgi/explore.cgi?pdbId=',
# 			    COMMON_NAME => '',
# 			    ORGANISM => 'Protein Data Bank',
# 			    ORGANISM_DB_NAME => 'PDB',
# 			    ORGANISM_DB_URL => 'http://www.rcsb.org/pdb/index.html',
# 			    DEFAULT_GENE_URL => 'http://www.rcsb.org/pdb/cgi/explore.cgi?pdbId'.'=104M',
# 			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa_pdb.README',
# 			    IDENTIFIER_2 => 'PDB_ID',
# 			    IDENTIFIER_3 => '',
# 			    IDENTIFIER_11 => '',
# 			    IDENTIFIER_2_EXAMPLE => '104M',
# 			    IDENTIFIER_3_EXAMPLE => '',
# 			    IDENTIFIER_11_EXAMPLE => '',
# 			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_pdb.txt',
# 			    ANNOTATION_FILE => 'gene_association.goa_pdb',
# 			    MENU_LABEL  => 'goa_pdb',
# 			    SLIM_MENU_LABEL  => 'goa_pdb (GOA GO slim)'
# 			    },
# 			goa_pdb_generic => {ANNOTATION_FILE => 'gene_association.goa_pdb_generic',
# 					    SLIM_MENU_LABEL  => 'goa_pdb (Generic GO slim)'
# 					    },
			goa_rat => {
			    # subsumed by RGD?
			    GENE_URL => 'http://www.ensembl.org/Rattus_norvegicus/geneview?gene=',
			    COMMON_NAME => 'Rat',
			    ORGANISM => 'Rattus norvegicus',
			    ORGANISM_DB_NAME => 'GOA @EBI',
			    ORGANISM_DB_URL => 'http://www.ebi.ac.uk/GOA/',
			    DEFAULT_GENE_URL => 'http://www.ensembl.org/Rattus_norvegicus/geneview?gene'.'=ENSRNOG00000017002&db'.'=core',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/goa.README',
			    IDENTIFIER_2 => 'UniProt_Accession (or Ensembl_ID)',
			    IDENTIFIER_3 => 'UniProt_ID (or Ensembl_ID)',
			    IDENTIFIER_11 => 'International Protein Index',
			    IDENTIFIER_2_EXAMPLE => 'P18090',
			    IDENTIFIER_3_EXAMPLE => 'B1AR_RAT',
			    IDENTIFIER_11_EXAMPLE => 'IPI00188184',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/goa_rat.txt',
			    CONVERSION_TOOL => $uniprot,
			    ANNOTATION_FILE => 'gene_association.goa_rat',
			    },
#			goa_rat_generic => {ANNOTATION_FILE => 'gene_association.goa_rat_generic',
#					    SLIM_MENU_LABEL  => 'goa_rat (Generic GO slim)'
#					    },
			goa_uniprot => {
			    GENE_URL => undef,
			    ORGANISM => 'undef',
			    ANNOTATION_FILE => 'gene_association.goa_uniprot', 
# UNUSED???
#			    MENU_LABEL  => 'goa_uniprot',
#			    SLIM_MENU_LABEL  => 'goa_unipro (Generic GO slim)'
			    },
			goa_zebrafish => {
			    ORGANISM => 'Danio rerio',
			    #  subsumed by ZFIN file
			    },
			gramene_oryza => {
			    GENE_URL => 'http://www.gramene.org/perl/protein_search?acc=',
			    COMMON_NAME => 'Rice',
			    ORGANISM => 'Oryza sativa',
			    ORGANISM_DB_NAME => 'Gramene',
			    ORGANISM_DB_URL => 'http://www.gramene.org/',
			    DEFAULT_GENE_URL => 'http://www.gramene.org/perl/protein_search?acc'.'=Q94HJ1',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/gramene_oryza.README',
			    IDENTIFIER_2 => 'Swiss-Prot/TrEMBL_ID',
			    IDENTIFIER_3 => 'Gene Name/Symbol',
			    IDENTIFIER_11 => '',
			    IDENTIFIER_2_EXAMPLE => 'Q94HJ1',
			    IDENTIFIER_3_EXAMPLE => 'OJ991113_30.2',
			    IDENTIFIER_11_EXAMPLE => '',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/gramene_oryza.txt',
			    ANNOTATION_FILE => 'gene_association.gramene_oryza',
			    MENU_LABEL  => 'Gramene (Rice - O. sativa)',
			    SLIM_MENU_LABEL  => 'Gramene (Generic GO slim)'
			    },
			mgi => {
			    GENE_URL => 'http://www.informatics.jax.org/searches/accession_report.cgi?id='.'<REPLACE_DBID>', 
			    COMMON_NAME => 'Mouse',
			    ORGANISM => 'Mus musculus',
			    ORGANISM_DB_NAME => 'MGI',
			    ORGANISM_DB_URL => 'http://www.informatics.jax.org/',
			    DEFAULT_GENE_URL => 'http://www.informatics.jax.org/searches/accession_report.cgi?id'.'=MGI:1889008',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/mgi.README',
			    IDENTIFIER_2 => 'MGI_ID',
			    IDENTIFIER_3 => 'Gene Symbol',
			    IDENTIFIER_11 => 'Gene_Symbol (old)',
			    IDENTIFIER_2_EXAMPLE => 'MGI:1889008',
			    IDENTIFIER_3_EXAMPLE => 'Atp2c1',
			    IDENTIFIER_11_EXAMPLE => '1700121J11Rik',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/mgi.txt',
			    ANNOTATION_FILE => 'gene_association.mgi',
			    MENU_LABEL  => 'MGI (Mouse - M. musculus)',
			    SLIM_MENU_LABEL  => 'MGI (Generic GO slim)'
			    },
			pseudocap => {
			    GENE_URL => 'http://www.pseudomonas.com/AnnotationByPAU.asp?PA=',
			    COMMON_NAME => 'Pseudomonas',
			    ORGANISM => 'Pseudomonas aeruginosa PAO1',
			    ORGANISM_DB_NAME => 'PseudoCAP',
			    ORGANISM_DB_URL => 'http://v2.pseudomonas.com/',
			    DEFAULT_GENE_URL => 'http://www.pseudomonas.com/AnnotationByPAU.asp?PA=PA4765',
			    README_URL => '',
			    IDENTIFIER_2 => 'PA#',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Alt. Gene Name (opt.)',
			    IDENTIFIER_2_EXAMPLE => 'PA4765',
			    IDENTIFIER_3_EXAMPLE => 'omlA',
			    IDENTIFIER_11_EXAMPLE => 'oprX',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/pseudocap.txt',
			    ANNOTATION_FILE => 'gene_association.pseudocap',
			    MENU_LABEL  => 'PseudoCAP (P. aeruginosa)',
			    SLIM_MENU_LABEL  => 'PseudoCAP (Generic GO slim)'
			    },
			rgd => {
			    GENE_URL => 'http://rgd.mcw.edu/tools/genes/genes_view.cgi?id=',
			    COMMON_NAME => 'Rat',
			    ORGANISM => 'Rattus norvegicus',
			    ORGANISM_DB_NAME => 'RGD',
			    ORGANISM_DB_URL => 'http://rgd.mcw.edu/',
			    DEFAULT_GENE_URL => 'http://rgd.mcw.edu/tools/genes/genes_view.cgi?id'.'=RGD:3696',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/rgd.README',
			    IDENTIFIER_2 => 'RGD_ID (or Ensembl Id, or UniProt accession)',
			    IDENTIFIER_3 => 'Gene Symbol (or UniProt Entry Name)',
			    IDENTIFIER_11 => 'if GOA-provided, an International Protein Index identifier',
			    IDENTIFIER_2_EXAMPLE => 'RGD:3696',
			    IDENTIFIER_3_EXAMPLE => 'Slc1a1',
			    IDENTIFIER_11_EXAMPLE => 'EAAC1',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/rgd.txt',
			    ANNOTATION_FILE => 'gene_association.rgd',
			    MENU_LABEL  => 'RGD (Rat - R. novegicus)',
			    SLIM_MENU_LABEL  => 'RGD (Generic GO slim)'
			    },
#			rgd_synonyms => {
#			    # augmented rgd
#			    GENE_URL => 'http://rgd.mcw.edu/tools/genes/genes_view.cgi?id=',
#			    COMMON_NAME => 'Rat',
#			    ORGANISM => 'Rattus norvegicus',
#			    ORGANISM_DB_NAME => 'RGD + XREFS',
#			    ORGANISM_DB_URL => 'http://rgd.mcw.edu/',
#			    DEFAULT_GENE_URL => 'http://rgd.mcw.edu/tools/genes/genes_view.cgi?id'.'=RGD:3696',
#			    README_URL => 'http://www.geneontology.org/gene-associations/readme/rgd.README',
#			    IDENTIFIER_2 => 'RGD_ID (or Ensembl Id, or UniProt accession)',
#			    IDENTIFIER_3 => 'Gene Symbol (or UniProt Entry Name)',
#			    IDENTIFIER_11 => 'International Protein Index identifier, additional synonyms',
#			    IDENTIFIER_2_EXAMPLE => 'RGD:3696',
#			    IDENTIFIER_3_EXAMPLE => 'Slc1a1',
#			    IDENTIFIER_11_EXAMPLE => 'EAAC1',
#			    SAMPLE_GENE_LIST => '/sampleGeneFiles/rgd_synonyms.txt',
#			    ANNOTATION_FILE => 'gene_association.rgd_synonyms',
#			    MENU_LABEL  => 'RGD with synonyms (Rat - R. novegicus)',
#			    SLIM_MENU_LABEL  => 'RGD with synonyms (Generic GO slim)'
#			    },
			sgd => {
			    GENE_URL => 'https://www.yeastgenome.org/locus/',
			    COMMON_NAME => 'Yeast',
			    ORGANISM => 'Saccharomyces cerevisiae',
			    ORGANISM_DB_NAME => 'SGD',
			    ORGANISM_DB_URL => 'https://www.yeastgenome.org/',
			    DEFAULT_GENE_URL => 'https://www.yeastgenome.org/locus/YPL250C',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/sgd.README',
			    IDENTIFIER_2 => 'SGD_ID',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Systematic ORF Name',
			    IDENTIFIER_2_EXAMPLE => 'S0006171',
			    IDENTIFIER_3_EXAMPLE => 'ICY2',
			    IDENTIFIER_11_EXAMPLE => 'YPL250C',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/sgd.txt',
			    ANNOTATION_FILE => 'gene_association.sgd',
			    MENU_LABEL  => 'SGD (Yeast - S. cerevisiae)',
			    SLIM_MENU_LABEL  => 'SGD (Yeast - S. cerevisiae GO slim)'
			    },
			sgd_generic => {
			    ANNOTATION_FILE => 'gene_association.sgd_generic',
			    SLIM_MENU_LABEL  => 'SGD (Generic GO slim)'
			    },
			tair  => {
#			    GENE_URL => 'http://www.arabidopsis.org/servlets/TairObject?type=gene&name=',
			    GENE_URL => 'http://www.arabidopsis.org/servlets/Search?type=general&search_action=detail&method=1&show_obsolete=F&sub_type=gene&SEARCH_EXACT=4&SEARCH_CONTAINS=1&name=',
			    COMMON_NAME => 'Common wallcress',
			    ORGANISM => 'Arabidopsis thaliana',
			    ORGANISM_DB_NAME => 'TAIR',
			    ORGANISM_DB_URL => 'http://www.arabidopsis.org/',
#			    DEFAULT_GENE_URL => 'http://www.arabidopsis.org/servlets/TairObject?type'.'=gene&name'.'=AT3G52270.1',
			    DEFAULT_GENE_URL => 'http://www.arabidopsis.org/servlets/Search?type=general&search_action=detail&method=1&show_obsolete=F&name=AT1G57980&sub_type=gene&SEARCH_EXACT=4&SEARCH_CONTAINS=1',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/tair.README',
			    IDENTIFIER_2 => 'TAIR Accession',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Gene Alias',
			    IDENTIFIER_2_EXAMPLE => 'gene:2100553',
			    IDENTIFIER_3_EXAMPLE => 'AT3G52270.1',
			    IDENTIFIER_11_EXAMPLE => 'T25B15.40',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/tair.txt',
			    ANNOTATION_FILE => 'gene_association.tair',
			    MENU_LABEL  => 'TAIR (Common wallcress - A. thaliana)',
			    SLIM_MENU_LABEL  => 'TAIR (Generic GO slim)'
			    },
			jcvi_Banthracis => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => '',
			    ORGANISM => 'Bacillus anthracis',
			    ORGANISM_DB_NAME => 'JCVI anthracis',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=gba',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus='.'BA0001',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'BA0001',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'dnaA',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_anthracis.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Banthracis',
			    MENU_LABEL  => 'JCVI_Banthracis (B. anthracis)',
			    SLIM_MENU_LABEL  => 'JCVI_Banthracis (Generic GO slim)'
			    },
			jcvi_Cburnetii => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => '',
			    ORGANISM => 'Coxiella burnetii',
			    ORGANISM_DB_NAME => 'JCVI coxiella',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=gcb',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus='.'CBU0001',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'CBU0001',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'dnaA',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_coxiella.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Cburnetii',
			    MENU_LABEL  => 'JCVI_Cburnetii (C. burnetii)',
			    SLIM_MENU_LABEL  => 'JCVI_Cburnetii (Generic GO slim)'
			    },
			jcvi_Cjejuni => {
			    ORGANISM => 'Campylobacter jejuni',
			    COMMON_NAME => '',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    ANNOTATION_FILE => 'gene_association.jcvi_Cjejuni',
			    MENU_LABEL  => 'JCVI_Cjejuni (C. jejuni)',
			    SLIM_MENU_LABEL  => 'JCVI_Cjejuni (Generic GO slim)'
			    },
			jcvi_Dethenogenes => {
			    ORGANISM => 'Dehalococcoides ethenogenes',
			    COMMON_NAME => '',
			    ANNOTATION_FILE => 'gene_association.jcvi_Dethenogenes',
			    MENU_LABEL  => 'JCVI_Dethenogenes (D. ethenogenes)',
			    SLIM_MENU_LABEL  => 'JCVI_Dethenogenes (Generic GO slim)'
			    },
			jcvi_Gsulfurreducens => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => 'Geobacter',
			    ORGANISM => 'Geobacter sulfurreducens PCA',
			    ORGANISM_DB_NAME => 'JCVI Gsulfurreducens',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=ggs',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus'.'=GSU0001',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'GSU_0001',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'dnaN',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_gsulfurreducens.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Gsulfurreducens',
			    MENU_LABEL  => 'JCVI_Gsulfurreducens (G. sulfurreducens PCA)',
			    SLIM_MENU_LABEL  => 'JCVI_Gsulfurreducens (Generic GO slim)'
			    },                      
			jcvi_Lmonocytogenes => {
#			    GENE_URL => undef,
			    ORGANISM => 'Listeria monocytogenes',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    ANNOTATION_FILE => 'gene_association.jcvi_Lmonocytogenes', 
			    MENU_LABEL  => 'JCVI_Lmonocytogenes (L. monocytogenes)',
			    SLIM_MENU_LABEL  => 'JCVI_Lmonocytogenes (Generic GO slim)' 
			    },
			jcvi_Mcapsulatus => {
			    ORGANISM => 'Methylococcus capsulatus',
			    COMMON_NAME => '',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    ANNOTATION_FILE => 'gene_association.jcvi_Mcapsulatus',
			    MENU_LABEL  => 'JCVI_Mcapsulatus (M. capsulatus)',
			    SLIM_MENU_LABEL  => 'JCVI_Mcapsulatus (Generic GO slim)' 
			    },
			jcvi_Psyringae => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => '',
			    ORGANISM => 'Pseudomonas syringae',
			    ORGANISM_DB_NAME => 'JCVI Psyringae',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=gps',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus'.'=PSPTO5598',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'PSPTO5598',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'atpC',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_psyringae.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Psyringae',
			    MENU_LABEL  => 'JCVI_Psyringae (P. syringae)',
			    SLIM_MENU_LABEL  => 'JCVI_Psyringae (Generic GO slim)'
			    },
			jcvi_Soneidensis => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => '',
			    ORGANISM => 'Shewanella oneidensis',
			    ORGANISM_DB_NAME => 'JCVI shewanella',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=gsp',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus'.'=SO0001',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'SO0001',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'mioC',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_shewannella.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Soneidensis',
			    MENU_LABEL  => 'JCVI_Soneidensis (S. oneidensis)',
			    SLIM_MENU_LABEL  => 'JCVI_Soneidensis (Generic GO slim)'
			    },
			jcvi_Spomeroyi => {
			    ORGANISM => 'Silicibacter pomeroyi',
			    COMMON_NAME => '',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    ANNOTATION_FILE => 'gene_association.jcvi_Spomeroyi',
			    MENU_LABEL  => 'JCVI_Spomeroyi (S. pomeroyi)',
			    SLIM_MENU_LABEL  => 'JCVI_Spomeroyi (Generic GO slim)'
			    },
#			jcvi_Tbrucei_chr2 => {
##			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db=tba1&;orf=',
#			    COMMON_NAME => '',
#			    ORGANISM => 'Trypanosoma brucei',
#			    ORGANISM_DB_NAME => 'JCVI Tbrucei chr2',
##			    ORGANISM_DB_URL => 'http://www.jcvi.org/tdb/e2k1/tba1/',
##			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db'.'=tba1&;orf'.'=Tb927.2.5850',
#			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
#			    IDENTIFIER_2 => 'JCVI Locus Name',
#			    IDENTIFIER_3 => 'JCVI Locus Name',
#			    IDENTIFIER_11 => '',
#			    IDENTIFIER_2_EXAMPLE => 'Tb927.2.5850',
#			    IDENTIFIER_3_EXAMPLE => '1F7.295',
#			    IDENTIFIER_11_EXAMPLE => '',
#			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_tbrucei_chr2.txt',
#			    ANNOTATION_FILE => 'gene_association.jcvi_Tbrucei_chr2',
#			    MENU_LABEL  => 'JCVI_Tbrucei_chr2 (T. brucei)',
#			    SLIM_MENU_LABEL  => 'JCVI_Tbrucei_chr2 (Generic GO slim)'
#			    },
			jcvi_Vcholerae => {
#			    GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus=',
			    COMMON_NAME => 'Cholera spirillum',
			    ORGANISM => 'Vibrio cholerae',
			    ORGANISM_DB_NAME => 'JCVI vibrio',
#			    ORGANISM_DB_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenomePage3.spl?database'.'=gvc',
#			    DEFAULT_GENE_URL => 'http://www.jcvi.org/tigr-scripts/CMR2/GenePage.spl?locus'.'=VC0112',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
			    IDENTIFIER_2 => 'JCVI Locus Name',
			    IDENTIFIER_3 => '',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'VC0112',
			    IDENTIFIER_3_EXAMPLE => '',
			    IDENTIFIER_11_EXAMPLE => 'cycA',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_vibrio.txt',
			    ANNOTATION_FILE => 'gene_association.jcvi_Vcholerae',
			    MENU_LABEL  => 'JCVI_Vcholerae (V. cholerae)',
			    SLIM_MENU_LABEL  => 'JCVI_Vcholerae (Generic GO slim)'
			    },
#			jcvi_gene_index => {
##			    GENE_URL => undef,
#			    COMMON_NAME => 'Gene Index',
#			    ORGANISM => '',
#			    ORGANISM_DB_NAME => 'JCVI gene index',
##			    ORGANISM_DB_URL => 'http://www.jcvi.org/tdb/tgi/index.shtml',
##			    DEFAULT_GENE_URL => '',
#			    README_URL => 'http://www.geneontology.org/gene-associations/readme/jcvi_prokaryotic.README',
#			    IDENTIFIER_2 => 'JCVI_TGI_ID',
#			    IDENTIFIER_3 => '',
#			    IDENTIFIER_11 => '',
#			    IDENTIFIER_2_EXAMPLE => 'Arabidopsis_TC171812',
#			    IDENTIFIER_3_EXAMPLE => '',
#			    IDENTIFIER_11_EXAMPLE => '',
#			    SAMPLE_GENE_LIST => '/sampleGeneFiles/jcvi_gene_index.txt',
#			    ANNOTATION_FILE => 'gene_association.jcvi_gene_index',
#			    MENU_LABEL  => 'JCVI_gene_index',
#			    SLIM_MENU_LABEL  => 'JCVI_gene_index (Generic GO slim)'
# 			    },
			wb => {
			    GENE_URL => 'http://www.wormbase.org/db/gene/gene?name=',
			    COMMON_NAME => 'Worm',
			    ORGANISM => 'Caenorhabditis elegans',
			    ORGANISM_DB_NAME => 'WormBase',
			    ORGANISM_DB_URL => 'http://www.wormbase.org/',
			    DEFAULT_GENE_URL => 'http://www.wormbase.org/db/gene/gene?name'.'=nhr-10',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/WormBase.README',
			    IDENTIFIER_2 => 'Protein Name',
			    IDENTIFIER_3 => 'Gene Name',
			    IDENTIFIER_11 => 'Gene Symbol',
			    IDENTIFIER_2_EXAMPLE => 'CE00815<A0>',
			    IDENTIFIER_3_EXAMPLE => 'nhr-10',
			    IDENTIFIER_11_EXAMPLE => 'B0280.8',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/wb.txt',
			    ANNOTATION_FILE => 'gene_association.wb',
			    MENU_LABEL  => 'WormBase (Worm - C. elegans)',
			    SLIM_MENU_LABEL  => 'WormBase (Generic GO slim)'
			    },
			zfin => {
			    GENE_URL => 'http://zfin.org/cgi-bin/webdriver?MIval=aa-markerview.apg&OID=',
			    COMMON_NAME => 'Zebrafish',
			    ORGANISM => 'Danio rerio',
			    ORGANISM_DB_NAME => 'ZFIN',
			    ORGANISM_DB_URL => 'http://zfin.org/cgi-bin/webdriver?MIval'.'=aa-ZDB_home.apg',
			    DEFAULT_GENE_URL => 'http://zfin.org/cgi-bin/webdriver?MIval'.'=aa-markerview.apg&OID'.'=ZDB-GENE-000125-12',
			    README_URL => 'http://www.geneontology.org/gene-associations/readme/zfin.README',
			    IDENTIFIER_2 => 'ZFIN_ID',
			    IDENTIFIER_3 => 'Gene Symbol',
			    IDENTIFIER_11 => '',
			    IDENTIFIER_2_EXAMPLE => 'ZDB-GENE-000125-12',
			    IDENTIFIER_3_EXAMPLE => 'igfbp2',
			    IDENTIFIER_11_EXAMPLE => '',
			    SAMPLE_GENE_LIST => '/sampleGeneFiles/zfin.txt',
			    ANNOTATION_FILE => 'gene_association.zfin',
			    MENU_LABEL  => 'ZFIN (Zebrafish - D. rerio)',
			    SLIM_MENU_LABEL  => 'ZFIN (Generic GO slim)'
			    }
			);


##############################################################################
# CLASS PRIVATE METHODS
#
##############################################################################
sub _annotationFileSuffix {
##############################################################################
# This class private method return gene annotation file suffix for the supplied 
# gene annotation file.

  my ($self, $annotationFile) = @_;

  if ($annotationFile) {
    my @annotationFileSuffix = split (/\./, $annotationFile);
    my $annotationFileSuffix = $annotationFileSuffix[$#annotationFileSuffix];

    return ($annotationFileSuffix);
  }
}


##############################################################################
# CLASS PUBLIC METHODS
#
##############################################################################
sub new {
##############################################################################
=pod

=head1 Constructor

=head2 new

This is the constructor for an MetaData object.

Usage:

   my $metaData = GO::AnnotationProvider::MetaData->new();

=cut

   my ($class) = @_;
   #---Create a new object
   my $self = bless { }, $class;
   
   return $self;                                     
}


=pod

=head1 Public Instance Methods

=cut

##############################################################################
sub AUTOLOAD {
##############################################################################
=pod

=head2 AUTOLOAD

This public AUTOLOAD method is used to get attributes and set attributes for an 
organism's gene annotation file for the supplied gene annotation file.

Usage:

   my $annotationFile = 'gene_association.sgd';
  
   #---Get this organism's annotation file extension (i.e. suffix)
   my @annotationFileSuffix = split (/\./, $annotationFile);
   my $annotationFileSuffix = $annotationFileSuffix[$#annotationFileSuffix];

   #MUTATOR METHODS
   #---Call this MetaData.pm's set method to set the value for ANNOTATION_FILE for this organism
   $metaData->setANNOTATION_FILE($file, $annotationFile);
   #---Call this MetaData.pm's set method to set the value for ANNOTATE_GENE_NUM for this organism
   $metaData->setANNOTATE_GENE_NUM($annotateGeneNum, $annotationFile);
   #---Call this MetaData.pm's set method to set the value for ESTIMATE_GENE_NUM for this organism
   $metaData->setESTIMATE_GENE_NUM($annotationFile);

   #ACCESSOR METHODS
   #---Call this MetaData.pm's get method to get organism gene url
   my ($organismGeneUrl) = $metaData->getGENE_URL($annotationFile);
   #---Call this MetaData.pm's get method to get organism common name 
   my ($organismCommonName) = $metaData->getCOMMON_NAME($annotationFile);
   #---Call this MetaData.pm's get method to get organism scientific name
   my ($ogranismScientificName) = $metaData->getORGANISM($annotationFile);
   #---Call this MetaData.pm's get method to get organism database name
   my ($organismDatabaseName) = $metaData->getORGANISM_DB_NAME($annotationFile);
   #---Call this MetaData.pm's get method to get organism database url
   my ($organismDatabaseUrl) = $metaData->getORGANISM_DB_URL($annotationFile);
   #---Call this MetaData.pm's get method to get all the attributes about this organism
   my ($organismGeneAsscFileRef) = $metaData->getOrganismInfo($annotationFile);

=cut

   my ($self, $annotationFile) = @_;

   #---Get the annotation file's file extension (i.e. suffix)
   my $annotationFileSuffix = $self->_annotationFileSuffix($annotationFile);
   #$DEBUG && print "annotationFileSuffix: $annotationFileSuffix\n";
  
   #$DEBUG && print "AUTOLOAD is set to ", $AUTOLOAD, "\n";
   my ($getORsetMethod, $getORsetAttribute) = ( $AUTOLOAD =~ /(get|set)(\w+)/);
   #$DEBUG && print "\$getORsetMethod: ", $getORsetMethod, "  \$getORsetAttribute: ", $getORsetAttribute, "\n"; 

 if ($getORsetMethod) {
   #---AUTOLOAD accessor methods
   if ($getORsetMethod eq 'get') {
   
      #AUTOLOAD accessor method to get all the class data attributes for this organism (e.g. getOrganismInfo)
      if ($getORsetAttribute eq 'OrganismInfo') {
         return ($_annotationFiles{ $annotationFileSuffix }); #This returns reference
      }#if ($getORsetAttribute eq 'OrganismInfo')
      
      #AUTOLOAD accessor methods to get a specific class data attribute for this organism (e.g. getGENE_URL, getCOMMON_NAME, getORGANISM, getORGANISM_DB_NAME, getORGANISM_DB_URL)
      else {
         return ( $_annotationFiles{ $annotationFileSuffix }->{ $getORsetAttribute } ); #This returns value
      }
   }#end if ($getORsetMethod eq 'get')


   #---AUTOLOAD mutator methods
   elsif ($getORsetMethod eq 'set') {

      #AUTOLOAD mutator method to set value for ESTIMATE_GENE_NUM attribute (e.g. setESTIMATE_GENE_NUM)
      if ($getORsetAttribute eq 'ESTIMATE_GENE_NUM') {
         if ($_annotationFiles{ $annotationFileSuffix }->{ORGANISM} ) {
            $_annotationFiles{ $annotationFileSuffix }->{$getORsetAttribute} = $organismEstimateTotalGeneNum { $_annotationFiles{ $annotationFileSuffix }->{ORGANISM} };
         }                               
         else {
            $_annotationFiles{ $annotationFileSuffix }->{$getORsetAttribute} = '';
         }
   
         $DEBUG && print "$getORsetAttribute: ", $_annotationFiles{ $annotationFileSuffix }->{$getORsetAttribute}, "\n";
      }#end if ($getORsetAttribute eq 'ESTIMATE_GENE_NUM')

      #AUTOLOAD mutator methods to set values for some of this class's data attributes to newValue (e.g. setANNOTATION_FILE, setANNOTATE_GENE_NUM)
      else {
         my ($self, $newValue, $annotationFile) = @_;

         #---Get the annotation file's file extension (i.e. suffix)
         my $annotationFileSuffix = $self->_annotationFileSuffix($annotationFile);
         $DEBUG && print "annotationFileSuffix: $annotationFileSuffix\n";

         $_annotationFiles{ $annotationFileSuffix }->{$getORsetAttribute} = $newValue;   
         $DEBUG && print "$getORsetAttribute: ", $_annotationFiles{ $annotationFileSuffix }->{$getORsetAttribute}, "\n";
         
      }#end else
    
   }#end elsif ($getORsetMethod eq 'set')

   else { croak "No such method:  ", $AUTOLOAD, "\n"; }
 }
}

##############################################################################
sub createGeneAsscTable {
##############################################################################
=pod

=head2 createGeneAsscTable

This public method creates a html table of the gene annotation file(s) available at GO ftp site 
for the supplied reference to an array of hash reference(s), whose key is the gene annotation 
file suffix and whose value is the reference to all the attributes of the organims.  The html  
table is written to the specified filepath (2nd argument).

An example of a html table of the gene annotation files created by this public method can 
be viewed at http://go.princeton.edu/GOTermFinder/GOTermFinder_help.shtml#asscFile

Usage:

   $metaData->createGeneAsscTable(\@organismsInfoArray, $filepath, $relativeUrl);
   

Usage Example:

   use GO::AnnotationProvider::AnnotationParser;
   use go::AnnotationProvider::MetaData;
 

   my $metaData = GO::AnnotationProvider::MetaData->new();
   my $Dir = '/usr/local/go/lib/GO/'; #Directory where the GO and gene annotation files downloaded from GO ftp site locate
   my $relativeUrl = "/goFiles/"; # a URL relative to the DOCUMENT_ROOT, where can the associations file be found (or linked to).

   opendir (DIR, $Dir) or die("Error opening: $!");
   my @organismsInfoArray;
   foreach my $file (readdir(DIR)) {
      if ($file !~ m/ontology/) {
         my $annotationFilePath = $Dir.$file; 
    
         # Get this organism's total annotated gene number
         my $annotationParser = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotationFilePath);
         my @databaseIds = $annotationParser->allDatabaseIds();
         my $annotateGeneNum = scalar(@databaseIds);

         #---Get this organism's annotation file extension (i.e. suffix)
         my @annotationFileSuffix = split (/\./, $file);
         my $annotationFileSuffix = $annotationFileSuffix[$#annotationFileSuffix];

         # Call these mutator methods to set values of these attributes for this organism
         $metaData->setANNOTATION_FILE($file, $annotationFileSuffix);
         $metaData->setANNOTATE_GENE_NUM($annotateGeneNum, $annotationFileSuffix);
         $metaData->setESTIMATE_GENE_NUM($annotationFileSuffix);

         # Call this accessor method to return a hash reference of all attributes for this organism
         my ($organismInfo) = $metaData->getOrganismInfo($annotationFileSuffix);
         # @organismsInfoArray contains hash references of attributes for all the organisms
         push(@organismsInfoArray, $organismInfo);  
      }
   } 

   # Call this method to create an html table of all the gene association files 
   my $filepath = "/Genomics/curtal/www/go/html/GOTermMapper/MetaData.html";
   $metaData->createGeneAsscTable(\@organismsInfoArray, $filepath, $relativeUrl);

   closedir(DIR);

=cut

   my ($self, $organismGeneAsscFilesArrayRef, $filepath, $relativeUrl) = @_;

   #dereference referenced variables
   my @organismGeneAsscFilesArray = @$organismGeneAsscFilesArrayRef;

   my @rows;

   foreach my $geneAsscFile (@organismGeneAsscFilesArray) {
      
      my $commonName = $geneAsscFile->{COMMON_NAME};
      my $organism = $geneAsscFile->{ORGANISM};
      my $orgText = $organism;
      if($commonName){$orgText =  "$commonName - $orgText"; }

      my $organismDBName = $geneAsscFile->{ORGANISM_DB_NAME};

      my $organismDBUrl = $geneAsscFile->{ORGANISM_DB_URL};
      my $organismDBLink = "";
      if ($organismDBUrl) {
	  $organismDBLink = a({-href=>$organismDBUrl}, b($organismDBName));
      }

      my $defaultGeneUrl = $geneAsscFile->{DEFAULT_GENE_URL};
      my $defaultGeneUrlLink = "";
      if ($defaultGeneUrl) {
	  $defaultGeneUrlLink = a({-href=>$defaultGeneUrl}, "Default gene URL");
      }

      my $annotationFile = $geneAsscFile->{ANNOTATION_FILE};
      my $annotationFileLink = "";
      if ($annotationFile) {
	  $annotationFileLink = a({-href=>$relativeUrl.$annotationFile}, $annotationFile);
      }

      my $readMeUrl = $geneAsscFile->{README_URL};
      my $readMeUrlLink = ""; 
      if ($readMeUrl){
	  $readMeUrlLink = a({-href=>$readMeUrl}, "README");
      }

      my $annotateGeneNum = $geneAsscFile->{ANNOTATE_GENE_NUM};
      my $estimateGeneNum = $geneAsscFile->{ESTIMATE_GENE_NUM} || '';
      my $identifier_2 = $geneAsscFile->{IDENTIFIER_2} || '';
      my $identifier_3 = $geneAsscFile->{IDENTIFIER_3} || '';
      my $identifier_11 = $geneAsscFile->{IDENTIFIER_11} || '';
      my $identifier_2_example = $geneAsscFile->{IDENTIFIER_2_EXAMPLE} || '';
      my $identifier_3_example = $geneAsscFile->{IDENTIFIER_3_EXAMPLE} || '';
      my $identifier_11_example = $geneAsscFile->{IDENTIFIER_11_EXAMPLE} || '';
   
      my $sample_list = $geneAsscFile->{SAMPLE_GENE_LIST};
      my $sample_list_link = "";
      if ($sample_list) {
	  $sample_list_link = a({-href=>$sample_list}, "sample list");
      }

      my $conversionTool = $geneAsscFile->{CONVERSION_TOOL};
      my $conversionToolLink = "";
      if ($conversionTool ) {
	  # redefine if any were specified
	  foreach my $label (keys(%{$conversionTool})){
	      $conversionToolLink .= li(a({-href=>$$conversionTool{$label}}, $label));
	  }
	  $conversionToolLink = ul($conversionToolLink);
      }

      if($annotateGeneNum > 0){
	  my $row = 
	       Tr({-bgcolor=>"#DEB887"},
		  td({-align=>"left", -valign=>"top", -nowrap=>''}, '<font size=-1>', join(br(), $orgText, $organismDBLink, $defaultGeneUrlLink, $annotationFileLink, $readMeUrlLink), '</font>'),
		  td({-align=>"left", -valign=>"top", -nowrap=>''}, '<font size=-1>', $annotateGeneNum , '</font>'),
		  td({-align=>"left", -valign=>"top", -nowrap=>''}, '<font size=-1><b>',$estimateGeneNum, '</b></font>'),
		  td({-align=>"left", -valign=>"top", -nowrap=>''}, '<font size=-1>', join(br(), $identifier_2, $identifier_3, $identifier_11), '</font>'),
		  td({-align=>"left", -valign=>"top", -nowrap=>''}, '<font size=-1>', join(br(), $identifier_2_example, $identifier_3_example, $identifier_11_example, $sample_list_link), '</font>'),
		  td({-align=>"left", -valign=>"top"}, '<font size=-2>', $conversionToolLink, '</font>')
		  );

#      print $row."\n";
      push(@rows,$row);

      }else{
	  warn "$annotationFile has zero annotations (probably filtered or eliminated by GO consortium conventions)\n";
      }

   }#end foreach my $geneAsscFile (@organismGeneAsscFilesArray)

   #---Generate the requested gene association  table file
   open (HTML, ">$filepath") || die "count not open $filepath : $!";
      
   print HTML "<center>\n",
              "<a name=asscFiles></a>",
              "<table border=0 cellpadding=3>\n",
              "<tr>\n",
              "<th align=center nowrap colspan=\"6\"><font color=\"#993300\" size=\"+1\">Gene Association File Table<font></th>\n",
              "</tr>\n",

              "<tr bgcolor=#993300>\n",
                   "<th align=center>\n",
                        "<a href=\"http://www.geneontology.org/GO.current.annotations.shtml\">\n",
                        "<font color=#FFFFFF>Organism, Gene Associations, and Authority</font><\a></th>\n",
                   "<th align=center>\n",
                        "<a href=\"http://www.geneontology.org/GO.current.annotations.shtml\">\n",
                        "<font color=#FFFFFF>Total Annotated Gene Products</font></a></th>\n",
                   "<th align=center><font color=#FFFFFF>Total Estimated Gene Products</font></th>\n",
                   "<th align=center nowrap>\n",
#                        "<a href=\"http://www.geneontology.org/GO.annotation.html#file\">\n",
#                        "<font color=#FFFFFF>Identifiers</font></a></th>\n",
                        "<font color=#FFFFFF>Identifiers</font></th>\n",
                   "<th align=center nowrap><font color=#FFFFFF>Example IDs</font></th>\n",
                   "<th align=center><font color=#FFFFFF>Identifier Conversion Tool(s)</font></th>\n",
              "</tr>\n";
   
   print HTML "@rows";
         
   print HTML "\n</table>\n",
                "</center>\n";

   close(HTML);

}

##############################################################################
sub geneAnnotationFilesMenu {
##############################################################################
=pod

=head2 geneAnnotationFilesMenu

This public method returns a reference to an array of gene annotation
files and a reference to a hash, whose keys are the gene annotation
files and whose value are gene annotation file labels.  These returned
array and hash references can then be used to create GOTermFinder's
pull-down menu of gene annotation files.

Usage:
   
   my ($geneAssValuesArrayRef, $geneAssLabelsHashRef) = $metaData->geneAnnotationFilesMenu;

=cut    

    my ($self) = @_;

    return( $self->_menuValuesAndLables( labelKey => 'MENU_LABEL' ));
} 


##############################################################################
sub geneAnnotationSlimFilesMenu {
##############################################################################
=pod

=head2 geneAnnotationSlimFilesMenu

This public method returns a reference to an array of gene annotation
files and a reference to a hash, whose keys are the gene annotation
files and whose value are gene annotation file labels.  These returned
array and hash references can then be used to create a GOTermMapper's
pull-down menu of gene annotation files.

Usage:
   
   my ($geneAssValuesArrayRef, $geneAssLabelsHashRef) = $metaData->geneAnnotationSlimFilesMenu;

=cut    

    my ($self) = @_;

    return( $self->_menuValuesAndLables(labelKey => 'SLIM_MENU_LABEL') );
}


##############################################################################
sub _menuValuesAndLables {
##############################################################################
# given a key (MENU_LABEL or SLIM_MENU_LABEL), this private method
# returns a 2 references suitable to construct a CGI popup menu.
# Returned, in order :
# 1) reference to a array of menu values
# 2) reference to a hash of value to label
#

    my $self = shift;
    my %args = @_;

    my $labelKey = $args{'labelKey'};
    my $fileKey = 'ANNOTATION_FILE';

    my $check_dir;
    if ($args{'checkUsableDir'}) {
	$check_dir = $args{'checkUsableDir'};
    }

    my (@values, %labels);

    foreach my $annotationFileSuffix ( keys(%_annotationFiles) ) {
	next if( $_annotationFiles{ $annotationFileSuffix }->{UNUSABLE} );
	# if both a value and a label are defined, use them
	if( $_annotationFiles{ $annotationFileSuffix }->{$fileKey} &&
	    $_annotationFiles{ $annotationFileSuffix }->{$labelKey} ) {

	    push(@values, $_annotationFiles{ $annotationFileSuffix }->{$fileKey});
	    $labels{ $_annotationFiles{ $annotationFileSuffix }->{$fileKey} } = $_annotationFiles{ $annotationFileSuffix }->{$labelKey};

	}

    }

    @values = sort(@values);

    return(\@values, \%labels);
}


##############################################################################
sub checkUnusable {
##############################################################################
    my $self = shift;
    my %args = @_;

    my $check_dir = $args{dir};
    return undef unless ($check_dir);

    my @unusables;

    my $n = 0;
    foreach my $annotationFileSuffix ( keys(%_annotationFiles) ) {
	# check if the file is usable, as indicated by readability for now
	if( $_annotationFiles{ $annotationFileSuffix }->{ANNOTATION_FILE} ){
	    if (! -r $check_dir."/".$_annotationFiles{ $annotationFileSuffix }->{ANNOTATION_FILE}) {
		my %info;
		$info{ANNOTATION_FILE_SUFFIX} = $annotationFileSuffix;
		foreach my $key ("ORGANISM", "ORGANISM_DB_NAME", "MENU_LABEL") {
		    $info{$key} = $_annotationFiles{ $annotationFileSuffix }->{$key};
		}
		$_annotationFiles{ $annotationFileSuffix }->{UNUSABLE} = 1;
		$unusables[$n++] = \%info;
	    } else {
		$_annotationFiles{ $annotationFileSuffix }->{UNUSABLE} = 0;
	    }
	}
    }

    return \@unusables;
}


##############################################################################
sub organismEstimateTotalGeneNum {
##############################################################################
=pod

=head2 organismEstimateTotalGeneNum

This public method returns an organism's estimate total gene number for the  
supplied gene annotation file.

Usage:

   my ($estimateGeneNum) = $metaData->organismEstimateTotalGeneNum($annotionFile);

=cut

   my ($self, $annotationFile) = @_;

   #---Get the annotation file's file extension (i.e. suffix)
   my $annotationFileSuffix = $self->_annotationFileSuffix($annotationFile);
   my $organism = $_annotationFiles{ $annotationFileSuffix }->{ORGANISM};
   $DEBUG && print "annotationFileSuffix: $annotationFileSuffix, organism $organism\n";

   #---Get TOTAL_NUM_GENES for the annotation file, if TOTAL_NUM_GENES is defined
   my $totalNumGenes;
   if (($organism) && (defined($organismEstimateTotalGeneNum { $organism }))) {
      $totalNumGenes = $organismEstimateTotalGeneNum { $organism };
#   }
#   else {
#      $totalNumGenes = '';
   }
   
   return $totalNumGenes;  
}


##############################################################################
sub organismGeneUrl {
##############################################################################
=pod

=head2 organismGeneUrl

This public method returns an organism's gene url for the supplied gene url specified in the 
$opt_u variable. If no gene url specified in the $opt_u variable, the method returns the 
organism's default gene url for the supplied gene annotation file.

Usage:

   my $opt_u = 'http://genome-www4.stanford.edu/cgi-bin/SGD/locus.pl?locus=';
   my ($geneUrl) = $metaData->organismGeneUrl($annotationFile, $opt_u);

=cut

   my ($self, $annotationFile, $opt_u) = @_;

   #---Get the annotation file's file extension (i.e. suffix)
   my $annotationFileSuffix = $self->_annotationFileSuffix($annotationFile); 
   $DEBUG && print "annotationFileSuffix: $annotationFileSuffix\n";

   #---Get GENE_URL for the annotation file.
   #   If user specifies the geneUrl, then use the user specified geneUrl. Otherwise use the 
   #   geneUrl defined in the %annotationFiles hash
   my $geneUrl;
   if ($opt_u) { 
       $geneUrl = $opt_u;
   } else {
      if (defined($_annotationFiles{ $annotationFileSuffix }->{GENE_URL}) ) {
	  $geneUrl = $_annotationFiles{ $annotationFileSuffix }->{GENE_URL};
#	  $geneUrl .= "<REPLACE_THIS>" if ($geneUrl !~ /\<REPLACE_/);
      } else {
         $geneUrl = '';
      }
   }
   if (($geneUrl) && ($geneUrl !~ /\<REPLACE_/)) {
       $geneUrl .= "<REPLACE_THIS>";
   }

   return $geneUrl;
}


##############################################################################
sub organismFileExist {
##############################################################################
=pod

=head2 organismFileExist

This public method returns a boolean to indicate whether the supplied gene annotation file exists.

Usage:

   my ($organismFileExist) = $metaData->organismFileExist($annotationFile);

=cut
   
   my ($self, $annotationFile) = @_;
                          
   #---Get the annotation file's file extension (i.e. suffix)
   my $annotationFileSuffix = $self->_annotationFileSuffix($annotationFile);   
   $DEBUG && print "annotationFileSuffix: $annotationFileSuffix\n";

   #---Check if the annotation file exists
   if(exists($_annotationFiles{ $annotationFileSuffix }) ) {
      return(1);
   }
   else {
      return(0);
   }
}

1; #make sure the file returns true or require will fail



##############################################################################
# Additional POD (Plain Old Documentation) from here on down
##############################################################################

__END__

=pod

=head1 AUTHOR

Linda McMahan, lmcmahan@genomics.princeton.edu

=cut
