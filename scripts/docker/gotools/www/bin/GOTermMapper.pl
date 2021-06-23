#!/usr/bin/perl

##############################################################################
# PROGRAM NAME: GOTermMapper.pl
# DATE CREATED: July 2004
# AUTHOR: Linda McMahan <lmcmahan@genomics.princeton.edu>
#
# EXECUTE COMMAND:
# 1. perl GOTermMapper.pl -h -d '/tmp/' -a C -o goslim_yeast.2003 -g gene_association.sgd (query genome)
# 2. perl GOTermMapper.pl -h -d '/tmp/' -a C -o goslim_yeast.2003 -g gene_association.sgd t/data_files/sgd_sample_gene_list.txt (query 1 yeast gene list)
# 3. perl GOTermMapper.pl -h -d '/tmp/' -a C -o goslim_yeast.2003 -g gene_association.sgd sgd_sample_gene_list.txt genes2.txt (query 2 yeast gene lists)
# 4. perl GOTermMapper.pl -h -d '/tmp/' -a C -s goslim_TAIR_LM -g gene_association.tair (user specified slim ontology file)
#
# 5. perl GOTermMapper.pl -f testEmail -h -d '/Genomics/dulcian/www/tmp/' -e 'lmcmahan@genomics.princeton.edu' 
#                         -U 'http://helix.princeton.edu/tmp/testEmailgene_association.sgd_slimTerms.html' 
#                         -a C -o goslim_yeast.2003 -g gene_association.sgd (query genome and email the result to me)
#
#perl GOTermMapper.pl -o generic.0208 -a P -g gene_association.wb -h c_elegans_genes.txt | more
#
##############################################################################

use strict;
use warnings;
use diagnostics;

use CGI qw/:all :html3/;   # still need for Tr(), td()

use Getopt::Std;
use vars qw($opt_a $opt_o $opt_s $opt_g 
            $opt_d $opt_G $opt_P
            $opt_p 
            $opt_h 
            $opt_u
            $opt_f
            $opt_e $opt_U $opt_i $opt_O $opt_W $opt_T $opt_t $opt_I $opt_n $opt_S $opt_E $opt_w
            $opt_H $opt_M);


use Pod::Usage;

BEGIN { $ENV{'DEVUSER'} = "." if (!$ENV{'DEVUSER'}); }
use lib "/var/www/lib";
#use lib "/Genomics/GO/".$ENV{DEVUSER}."/lib";
#use lib "$ENV{HOME}/GO/lib64/perl5";
#use lib "$ENV{HOME}/GO/GO/lib";

use GO::AnnotationProvider::AnnotationParser;
use GO::OntologyProvider::OntologyParser;
use GO::OntologyProvider::OboParser;
use GO::Utils::File    qw (GenesFromFile);
use GO::Utils::General qw (CategorizeGenes);
use GO::AnnotationProvider::MetaData;

##############################################################################

$|=1;

#---Check for invalid program switches
if (! getopts('a:o:s:g:d:G:P:p:hu:f:e:U:i:O:W:T:t:I:S:E:w:HM')) {
   die "Usage: The program switch you entered is invalid\n";
}

#---Validate existence of directories 
if ($opt_d || $opt_G || $opt_P) {
   &validateDir($opt_d, $opt_G, $opt_P);
}

#---If user uses -H switch, use Pod::Usage to print program usage help message to the screen.
#   If user uses -M switch, use Pod::Usage to print program complete POD to the screen.
#   If user fails to pass the program REQUIRED parameters at the command line to the program, use
#      Pod::Usage to print warning message and synopsis from te program POD to the screen.
&checkUsage($opt_a, $opt_o, $opt_s, $opt_g, $opt_H, $opt_M); 

#---Variables declaration/initialization and get program parameters via Getopt module
# Debugging variable; set to 1 for printed feedback (i.e. to print debug print statements)
my $DEBUG = 0;

# Create a MetaData object
my $metaData = GO::AnnotationProvider::MetaData->new();

#---REQUIRED program parameters:
my $aspect = uc($opt_a);
my ($aspectExist, $ontologyAspect) = &getOntologyAspectInfo($aspect);
$DEBUG && print "Aspect: ", $aspect, " aspectExist= ", $aspectExist, " ontologyAspect: ", $ontologyAspect, "\n";
# Validate ontology aspect argument
&validateAspect($aspectExist);

#LATER:validate slim ontology file argument
my $ontologyFile = $opt_o;
$DEBUG && print "Slim ontology file: $ontologyFile\n";

#validate gene-association file argument
&validateGeneAsscFile($opt_g);  
my $annotationFile = $opt_g;
$DEBUG && print "Gene association file: $annotationFile\n";
my $annotationFileBase = $annotationFile;
$annotationFileBase =~ /([^\/]+)$/;
$annotationFileBase = $1;
$DEBUG && print "annotationFile $annotationFile\n";
$DEBUG && print "annotationFileBase $annotationFileBase\n";

my $fullOntology;   # if needed, we parse gene_ontology.obo - but we only do it once

#---OPTIONAL program parameters:
# Directory where the program output files write to
my $outDir = "/tmp/";
$outDir = $opt_d if($opt_d);

# Directory where GO slim files downloaded from GO ftp site locate
# my $goDir = "/Genomics/GO/data/unparsed_slim/";
my $goDir = "";
$goDir = $opt_G if($opt_G);

# Directory where parsed GO slim files locates
# my $goParseDir = "/Genomics/GO/data/parsed_slim/";
my $goParseDir = "";
$goParseDir = $opt_P if($opt_P);
$goParseDir = "x";   #!!! temporary workaround, bad parsed files?

# Path to map2slim program
# my $map2slimPath = "";
# my $map2slimPath = "/Genomics/GO/bin/map2slim";
my $map2slimPath = "/var/www/bin/map2slim";
$map2slimPath = $opt_p if ($opt_p);

# GOID url
my $goidUrl = 'https://www.yeastgenome.org/go/<REPLACE_THIS>';
# Get organism gene url
my $geneUrl = 'https://www.yeastgenome.org/locus/<REPLACE_THIS>';

# FOR GENOME QUERY, this process ID is obtained from GOTermMapper cgi script calling this 
# program through -f switch.  This process ID is used to concatenate to the text and html 
# output files making the genome query output text and html files somewhat unique
my $FileNamePID = $$;
$FileNamePID = $opt_f if($opt_f);


#---Email stuff: Info needed to email GO Term Mapper results to user through GO Term Mapper web tool
my $sendmail = "/usr/sbin/sendmail -n -t -oi";
my $date = scalar(localtime() );
my $email = $opt_e;
my $contactEmailAddress = "gotools\@genomics.princeton.edu";
my $GOTermMapperResultsUrl = $opt_U;
my $inputDataUrl = $opt_i;
my $GoSlimTermsOption = $opt_O;
my $userGoSlimTermWarning = $opt_W;
my $GoSlimTermsNotice = "<b>Please note</b> that the following report of ".
                        "<b>case(s) where no genes have annotation to GO slim term(s) in your GO slim list for your chosen ontology aspect</b>".
                        " is valid, if and only if the GO slim term(s) in your GO slim list is from the correct chosen ontology aspect.  ".
                        "In other words, the gene list might have annotation(s) to GO slim term(s) in your GO slim list for other ".
                        "ontology aspect(s) rather than the ontology aspect you had chosen (i.e. the GO slim term(s) in your GO slim list ".
                        "belongs to the other ontology aspects rather than the one you had chosen).  You might want to choose the correct ".
                        "ontology aspect corresponding to the GOID(s) in your input GO slim list.";
my $htmlTableLink = $opt_T;
my $plainTextLink = $opt_t;
my $inputDataLink = $opt_I;
#my $inputGenesNum = $opt_n;   #! not needed, not used
my $userGoSlimListLink = $opt_S;
my $entryMissingGoidMesg = $opt_E;
my $goWebServerUrl = $opt_w;

my @inputGenes;
my @inputDuplicates;

my ($ontology, $annotation, $annotationMetaFile, $annotationMeta, $ontologyUnparsedFile);

## turn off $opt_s
$opt_s = 0;


#---IF USE USER SPECIFIED ONTOLOGY SLIM FILE
if ($opt_s) {
   #---Get slim gene association file using user specified ontology slim file
   my $goSlimOntologyFile = $opt_s;
   my $slimGeneAsscFileName = $FileNamePID."slim_".$annotationFileBase;
   $annotationMetaFile = $outDir.$slimGeneAsscFileName.".meta";
   #LATER: CHECK FOR EXISTENCE OF $goSlimOntologyFile IN tmp directory
   my $sysCall;
   if ($annotationFile ne $annotationFileBase) {
       $sysCall = "$map2slimPath ".$goSlimOntologyFile." /var/www/data/gene_ontology.obo"." ".$annotationFile." -o $outDir".$slimGeneAsscFileName;
   } else {
       $sysCall = "$map2slimPath ".$goSlimOntologyFile." /var/www/data/gene_ontology.obo"." $goDir"."/".$annotationFileBase." -o $outDir".$slimGeneAsscFileName;
   }
   $DEBUG && print "\$sysCall:$sysCall\n";
   # print "Running map2slim to get slim association file ....\n";
   print "$sysCall", "\n";
   system($sysCall);    
   
   #---Parse user specified ontology slim file and slim gene association file,
   # Parse user specified ontology slim file
   my $ontologyFile = $goSlimOntologyFile;
   $ontologyUnparsedFile = $ontologyFile;
   print "Parsing ontology slim file ....\n";
   # Create ontology object
   if ($ontologyFile =~ /\.obo$/) {
       $ontology = GO::OntologyProvider::OboParser->new(ontologyFile => $ontologyFile, aspect => $aspect);
   } else {
       $ontology = GO::OntologyProvider::OntologyParser->new(ontologyFile => $ontologyFile);
   }

   # Parse slim gene association file
   my $annotationFile = $outDir.$slimGeneAsscFileName;
   print "Parsing slim gene association file $annotationFile ....\n";
   # Create annotation object
   $annotation = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotationFile);
  
}#end if ($opt_s)
#---END IF USE USER SPECIFIED ONTOLOGY SLIM FILE


#---IF NOT USE USER SPECIFIED ONTOLOGY SLIM FILE 
else {
   #---Determine whether to use parsed or unparsed slim ontology file
   my $ontologyParsedFile = $goParseDir."parsed_".$ontologyFile;
   $DEBUG && print "PARSED slim ontology file: $ontologyParsedFile\n";
   $ontologyUnparsedFile = $goDir."/".$ontologyFile;
   $DEBUG && print "UNPARSED slim ontology file: $ontologyUnparsedFile\n";
   # Create ontology object from preparsed ontology file
   if (-e $ontologyParsedFile) {
       print "Opening the preparsed $ontologyFile file ...\n";
       if ($ontologyParsedFile =~ /\.obo$/) {
	   $ontology = GO::OntologyProvider::OboParser->new(objectFile=>$ontologyParsedFile, aspect => $aspect);
       } else {
	   $ontology = GO::OntologyProvider::OntologyParser->new(objectFile=>$ontologyParsedFile);
       }
   }
   else {
      # Parse ontology slim file 
      print "Parsing the $ontologyFile file ...\n";
      # Create ontology object 
      if ($ontologyUnparsedFile =~ /\.obo$/) {
	  $ontology = GO::OntologyProvider::OboParser->new(ontologyFile=>$ontologyUnparsedFile, aspect => $aspect);
      } else {
	  $ontology = GO::OntologyProvider::OntologyParser->new(ontologyFile=>$ontologyUnparsedFile);
      }
   }   

   #---Determine whether to use parsed or unparsed gene associated slim file
   my ($annotationParsedFile, $annotationParsedFileName);
   my ($annotationUnparsedFile, $annotationUnparsedFileName);
   # if an absolute path, take as literal -- mark
   if ($annotationFile =~ /^\//) {
       $annotationUnparsedFile = $annotationFile;
       $annotationUnparsedFileName = $annotationFile;
       $annotationParsedFile = "$goParseDir/parsed_$annotationFile";  #! won't exist
       $annotationParsedFileName = "parsed_slim_".$annotationFile;    #! irrelevant
       #! no generic sense?
   } else {
       if ($ontologyFile =~ m/generic/) {
	   $annotationUnparsedFile = $goDir."/generic_slim_".$annotationFile;
	   $annotationUnparsedFileName = "generic_slim_".$annotationFile;   
	   $annotationParsedFile = $goParseDir."parsed_generic_slim_".$annotationFile;
	   $annotationParsedFileName = "parsed_generic_slim_".$annotationFile;
       }
       else {
	   $annotationUnparsedFile = $goDir."/slim_".$annotationFile;
	   $annotationUnparsedFileName = "slim_".$annotationFile;
	   $annotationParsedFile = $goParseDir."parsed_slim_".$annotationFile;
	   $annotationParsedFileName = "parsed_slim_".$annotationFile;
       }
   }
   $DEBUG && print "UNPARSED gene association file path: $annotationUnparsedFile\n";
   $DEBUG && print "PARSED gene association file path: $annotationParsedFile\n";

   if (-e $annotationParsedFile) {
      print "Opening the preparsed ", $annotationParsedFileName, " file ...\n";
      # Create annotation object from preparsed gene association slim file
      $annotation = GO::AnnotationProvider::AnnotationParser->new(objectFile => $annotationParsedFile);
   }
   else {
      # Parse the gene association slim file
      print "Parsing the ", $annotationUnparsedFileName, " file ...\n";
      # Create annotation object
      $annotation = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotationUnparsedFile);
   }

   $annotationMetaFile = $annotationUnparsedFile.".meta";
}#end else
#---End IF NOT USE USER SPECIFIED ONTOLOGY SLIM FILE

$DEBUG && print "Find meta ".$annotationMetaFile."\n";
if (-f $annotationMetaFile) {
    $annotationMeta = Storable::retrieve($annotationMetaFile);
    $DEBUG && print "Retrieved meta\n" if ($annotationMeta);
}

#---PARSING SLIM ONTOLOGY FILE to get all goids and their associated
#   terms (i.e. Key = goid, value = term) for the specified
#   aspect. $slimGoidsTermsHashRef is reference to a hash of all goids
#   and their associated terms (i.e. Key = goid, value = term) for the
#   specifed aspect in the slim ontology file.
my ($slimGoidsTermsHashRef) = allGoids4slimOntologyFile ($ontologyUnparsedFile, $ontologyAspect);

#---Get all databaseIds in the gene association file
my @databaseIds = $annotation->allDatabaseIds();
$DEBUG && print "Total databaseIds in annotation file:", scalar(@databaseIds), "\n";

#---Use the databaseIds to get # annotations associated with each goid
#   in the gene association file
my ($totalNumAnnotationsToGoIdHashRef) = totalNumAnnotationsToGoId ($annotation, $aspect, \@databaseIds);

#---Get total number of annotated genes in the gene association file
my $totalNumGenes = $annotation->numAnnotatedGenes();
$DEBUG && print "Total number of genes in the annotation file: $totalNumGenes\n";

#---START FIND SLIM TERMS FOR GENOME QUERY or GENES QUERY---------------------
if (!@ARGV) {
   
   #---Start find slim terms for the genome query
   # Use the databaseIds to get slim terms
   # $annotationsArrayRef is reference to an array of annotated goids.
   # $unannotate_goidsRef is referece to an array of unannotated goids.
   my ($annotationsArrayRef, $unannotate_goidsRef) = findSlimTerms($ontology, $annotation, $aspect, 
								   \@databaseIds, $slimGoidsTermsHashRef,
								   $totalNumAnnotationsToGoIdHashRef);

#   if (($annotationMeta) && ($annotationMeta->{lostDatabaseIDs}) && ($annotationMeta->{lostDatabaseIDs}->{$aspect})) {
#       push(@lostGenes, @{$annotationMeta->{lostDatabaseIDs}->{$aspect}});
#   }
   
   #Generate output text file (the default output)
   &generateTextFile($annotationsArrayRef, $totalNumGenes, $unannotate_goidsRef, $slimGoidsTermsHashRef,
                     $FileNamePID, $annotationFileBase, $outDir, $ontologyAspect);

   #If use -h switch, generate output html file
   if ($opt_h) {
      &generateHtmlFile($annotationsArrayRef, $totalNumGenes, $unannotate_goidsRef, $slimGoidsTermsHashRef,
                        $FileNamePID, $annotationFileBase, $outDir, $ontologyAspect);
   }

   if ($opt_e) {
       &sendEmail;
   }

}
else {
    #---Start find slim terms for the genes query
    &findSlimTerms4queryGenes($ontology, $annotation, $aspect, $ontologyAspect, $FileNamePID, $outDir, $opt_h, $geneUrl, 
                              $slimGoidsTermsHashRef, $totalNumAnnotationsToGoIdHashRef, $totalNumGenes);
}


##############################################################################
#  SUBROUTINES SECTION
#  
##############################################################################

##############################################################################
sub checkUsage {  
##############################################################################
   my ($opt_a, $opt_o, $opt_s, $opt_g, $opt_H, $opt_M) = @_;

   #---Use Pod::Usage to read and parse the POD section of the program
   #   -verbose => 0 (print synopsis)
   #   -verbose => 1 (print synopsis, options, argument)
   #   -verbose => 2 (print the whole pod)   
   # Print help message to the screen, when user uses -H program switch.
   pod2usage(-verbose => 1) && exit if ($opt_H);

   # Print the complet POD to the screen, when user uses -m program switch.
   pod2usage(-verbose => 2) && exit if ($opt_M);

   # Print the synopsis from the POD to the screen, when user fails to
   # pass the required program argument(s) at the command line to this
   # program.
   pod2usage(-message => "\nWARNING: You forgot to specify the program REQUIRED arguments: ontology aspect, gene-association file, OR
             ontology file at the command line.", -verbose => 0) && exit if (! $opt_a || ! $opt_g);

   pod2usage(-message => "\nWARNING: You forgot to specify the program REQUIRED argument: ontology file.",
             -verbose => 0) && exit if (! $opt_o && ! $opt_s);
}


##############################################################################
sub findSlimTerms4queryGenes {
##############################################################################
   my ($ontology, $annotation, $aspect, $ontologyAspect, $FileNamePID, $outDir, $opt_h, $geneUrl,
       $slimGoidsTermsHashRef, $totalNumAnnotationsToGoIdHashRef, $totalNumGenes) = @_;
   
   foreach my $file (@ARGV){
      #---Check if  input file containing list of genes exist
      &validateFile($file);

      print "Analyzing $file\n";
      #---Get the genes from the input file
      @inputGenes = &GenesFromFile($file);

      # Correct the bug in 'GenesFromFile' method which remove 1
      # leading whitespace but fails to remove multiple leading
      # whitespaces
      # Also remove any duplicates
      my @genes;
      my %geneCheck;
      foreach my $gene (@inputGenes) {
         $gene =~ s/\s+$//;
         # Correct the bug (i.e. $gene =~ s/^\s//;) in 'GenesFromFile' method         
         $gene =~ s/^\s+//; 
	 if ($geneCheck{$gene}) {
	     push(@inputDuplicates, $gene);
	     next;
	 }
	 $geneCheck{$gene} = 1;
         push(@genes, $gene);  
      }

      #---Now we have to decide which input genes we can analyze by
      #   categorizing them into those found in gene_association file
      #   (@list), those not found in gene association file (@notFound),
      #   and those found but are ambiguous (@ambiguous):
      my (@list, @notFound, @ambiguous);
      &CategorizeGenes(annotation  => $annotation,
		       genes       => \@genes,
		       ambiguous   => \@ambiguous,
		       unambiguous => \@list,
		       notFound    => \@notFound);
      my @unannotatedGenes;  # would be nice if CategorizeGenes found these

      if (!@list){
         print "No known genes exist in $file, so skipping.\n";

         #---Add this if statement for email to user using the GO Term Mapper web tool
         my $asscFilesHelpPageLink = $goWebServerUrl."/GOTermMapper/GOTermMapper_help.shtml#asscFiles";

         if ($email) {
          
             my $inputGeneListErrorMessage = "No known genes exist in Your Input Gene List (".
                                          $inputDataUrl.
		                          ") This could be caused by the following reasons:\n\n".
					  "1) The genes within your list have not been annotated yet.\n".
					  "2) You are using an unknown gene identifier for the selected ".
					  "association file (please refer ".$asscFilesHelpPageLink." )\n".
					  "3) You have chosen the wrong GO association file.\n\n";

             &sendEmail($inputGeneListErrorMessage);             

             exit;

         }

         next;
      }
      
      #---Get databaseIds for the input list of genes.
      # @databaseIds is array of databaseIds for the input genes.
      # %databaseId2OrigName is hash whose key is databaseId and value
      # is input gene identifier.
      my (@genesDatabaseIds, %genesOrigNames, @lostGenes); 
                                               
      foreach my $gene (@list) {
         # Get databaseId for this gene
	 #!! bandaid fix: databaseIdByName used to die if ambiguous,
	 #!! but with CategorizeGenes now checking for unambiguity of standard names,
	 #!! and not all code has been updated for this check, we could end up
	 #!! passing something that nameIsAmbiguous would flag as ambiguous.
	 #!! So now it doesn't die but returns undef for ambiguous names.
	 #!! nameIsAmbiguous should be updated, but that will require a review
	 #!! of all the code
         my $databaseId = $annotation->databaseIdByName($gene);
	 next if (!defined($databaseId));
         push (@genesDatabaseIds, $databaseId);
         $genesOrigNames { $databaseId } = $gene;
	 if (($annotationMeta) && ($annotationMeta->{lostDatabaseIDs}) && ($annotationMeta->{lostDatabaseIDs}->{$aspect})) {
	     foreach my $lostID (@{$annotationMeta->{lostDatabaseIDs}->{$aspect}}) {
		 if ($databaseId eq $lostID) {
		     push(@lostGenes, $gene);
		 }
	     }
	 }
      }

      if ($DEBUG) {
	  print "Determine databaseIds from genes\n";
	  foreach my $genesDatabaseId (@genesDatabaseIds) {
	      print "$genesDatabaseId\n";
	  }
	  print "Map databaseIds to genes\n"; 
	  while (my ($key, $value) = each(%genesOrigNames)) {
	      #key is databaseId and value is gene given in input file
	      print "$key => $value\n"; 
	  }
      }

      #---Use the genes' databaseIds to get slim terms.
      # $annotationsArrayRef is reference to an array of annotated
      # goids (i.e. goids having genes associated with them).
      # $unannotate_goidsRef is referece to an array of unannotated
      # goids (i.e. goids having no genes associated with them).

      my ($annotationsArrayRef, $unannotate_goidsRef) = findSlimTerms($ontology, $annotation, $aspect, 
								      \@genesDatabaseIds, $slimGoidsTermsHashRef, 
								      $totalNumAnnotationsToGoIdHashRef);   

      #---Get those genes in the input gene list annotated to each goid (i.e. get ANNOTATED_GENES)
      my $annotations = $annotationsArrayRef;
      my %nodeToIndex;
      for (my $i = 0; $i < scalar(@$annotations); $i++){
	  $nodeToIndex{$annotations->[$i]->{GOID}} = $i;
      }

      my %unannotatedHash;

      $DEBUG && print "Get genes annotated to each goid\n";
      foreach my $databaseId (@genesDatabaseIds) {
	  # Look at all goids for this databaseId.
	  my $allGOIDsForDatabaseIdArrayRef = $annotation->goIdsByDatabaseId(databaseId => $databaseId,
									     aspect     => $aspect);

          # For each goid for this databaseId, record this goid and its
          # ancestor goids.
	  my %allGOIDsForDatabaseId;
	  foreach my $goid (@{ $allGOIDsForDatabaseIdArrayRef }) {
	      $allGOIDsForDatabaseId{ $goid } = undef;
	      if( $ontology->nodeFromId($goid) ) {
		  my $node = $ontology->nodeFromId($goid);
		  foreach my $ancestor ($node->ancestors) {
		      $allGOIDsForDatabaseId{ $ancestor->goid } = undef;
		  }
	      }
	  }

	  my @allGOIDsForDatabaseId = keys(%allGOIDsForDatabaseId);

          # For this databaseID's goid and its ancestor goids, find
          # out those goids associated with the genes in the input
          # gene list, and get the gene names for these goids
          # associated genes using their databaseIds.
	  my $unannotated;
	  foreach my $goid (@allGOIDsForDatabaseId){

             # Skip those goids not assoicated with genes in the input gene list 
	      if (! exists $nodeToIndex{$goid}) {
		  $unannotated = 1 if (!defined($unannotated));
		  next;
	      }
	      $unannotated = 0;

             # If this goid associated with a gene in the input gene
	     # list, get the gene name for the gene using its
	     # databaseId.
	     $DEBUG && print "databaseId:$databaseId, nodeToIndex(goid):$nodeToIndex{$goid}\n";

	     $annotations->[$nodeToIndex{$goid}]->{ANNOTATED_GENES}->{$databaseId} = $genesOrigNames{ $databaseId };
	  }

	  if ($unannotated) {
	      $DEBUG && print "unannotated: $databaseId ".$genesOrigNames{$databaseId}."\n";
	      $unannotatedHash{$genesOrigNames{$databaseId}} = 1;
	  }
      }

      # do not duplicate lost genes in the unannotated gene list
      for my $lostGene (@lostGenes) {
	  delete($unannotatedHash{$lostGene});
      }
         
      @unannotatedGenes = keys %unannotatedHash;

      #---Generate output text file (the default output)
      &generateTextFile4queryGenes($totalNumGenes, \@genes, \@list,
				   \@ambiguous, \@notFound, \@lostGenes, \@unannotatedGenes,
				   $annotationsArrayRef,
				   $unannotate_goidsRef,
				   $slimGoidsTermsHashRef, $file,
				   $FileNamePID, $outDir, $ontologyAspect,
				   $totalNumAnnotationsToGoIdHashRef);

      #---If use -h switch, generate output html file        
      if ($opt_h) {
         &generateHtmlFile4queryGenes($totalNumGenes, \@list,
                                      \@ambiguous, \@notFound, \@lostGenes, \@unannotatedGenes,
                                      $annotationsArrayRef,
                                      $unannotate_goidsRef,
                                      $slimGoidsTermsHashRef, $file,
                                      $FileNamePID, $outDir, $ontologyAspect,
                                      $geneUrl,
                                      $totalNumAnnotationsToGoIdHashRef);
      }
                    
      if ($opt_e) {
         &sendEmail;
      }

   }
}


##############################################################################
sub generateTextFile4queryGenes {
##############################################################################
   my ($totalNumGenes, $inputGenesRef, $genesRef, $ambiguousRef,
       $notFoundRef, $lostRef, $unannotatedRef, $annotationsArrayRef, $unannotate_goidsRef,
       $slimGoidsTermsHashRef, $file, $FileNamePID, $outDir, $ontologyAspect,
       $totalNumAnnotationsToGoIdHashRef) = @_;

   #---Dereference referenced variables
   my @inputGenes = @$inputGenesRef;
   my @genes = @$genesRef;
   my @ambiguous = @$ambiguousRef;
   my @notFound = @$notFoundRef;
   my @annotationsArray = @$annotationsArrayRef;
   my @unannotate_goids = @$unannotate_goidsRef;
   my %slimGoidsTermsHash = %$slimGoidsTermsHashRef;
   my %totalNumAnnotationsToGoId = %$totalNumAnnotationsToGoIdHashRef;


   #---Work out the name of text file
   my $textFile = $FileNamePID.$file;
   my $tabFile = $FileNamePID.$file;
   # Delete anything up to and including the last slash
   $textFile =~ s/.*\///;
   $tabFile =~ s/.*\///;
   # Delete anything following the last period
   $textFile =~ s/\..*//;
   $tabFile =~ s/\..*//;
   # Now add an terms suffix
   $textFile .= "_slimTerms.txt";
   $tabFile .= "_slimTab.txt";
   my $textFilePath = $outDir.$textFile;
   my $tabFilePath = $outDir.$tabFile;
   $DEBUG && print "TextFilePath: $textFilePath\n";
   $DEBUG && print "TabFilePath: $tabFilePath\n";

   #---Open the text file to write
   open(TEXT, ">$textFilePath") or die "cannot create $textFilePath\n";
   open(TAB, ">$tabFilePath") or die "cannot create $tabFilePath\n";
   
   #---GENERATE OUTPUT TEXT FILE FOR THE QUERY GENES (the default output)
   $DEBUG && print "Write GOTermMapper result to text file ...\n";

   print TEXT "\nYour input list contains ".scalar(@inputGenes)." genes.\n";

   # Check if there is/are bad gene name in the gene list
   if (@inputDuplicates) {
       print TEXT "\nThese ",$#inputDuplicates+1," identifier(s) are duplicated in your input list: ", join(" ", @inputDuplicates), "\n";
       
   }
   if (@ambiguous) {
       print TEXT "\nThese ",$#ambiguous+1," identifier(s) are found to be ambiguous: ", join(" ", @ambiguous), "\n";
   }
   if (@notFound) {
       # print TEXT "\nThese ",$#notFound+1," identifier(s) are found to be unannotated: ", join(" ", @notFound), "\n";
       print TEXT "\nThese ",$#notFound+1," identifier(s) represent either invalid gene names, dubious ORFs unlikely to encode functional proteins or genes which are currently unannotated: ", join(" ", @notFound), "\n"; 
   }
   if (@{$lostRef}) {
       print TEXT "\nThese ",$#{$lostRef}+1, " identifier(s) are not annotated in the slim, but they had non-root annotations that are not in the slim: ", join(" ", @{$lostRef}), "\n";
   }
   if (@{$unannotatedRef}) {
       # print TEXT "\nThese ",$#{$unannotatedRef}+1, " identifiers had no non-root annotations: ", join(" ", @{$unannotatedRef}),"\n";
       print TEXT "\nThese ",$#{$unannotatedRef}+1, " identifier(s) represent valid gene names that either could not be mapped to terms in the current GO slim set or are currently annotated to the root node for the slim set being used: ", join(" ", @{$unannotatedRef}),"\n"; 

   }

#   my $badGeneNameMessage = '';
#   if (@ambiguous || @notFound) {
#      $badGeneNameMessage = "\nYour Input List of Genes (".scalar(@inputGenes)." genes)\n".
#                            "\nThe following gene(s) is/are not recognized as a valid gene name in ".$annotationFile.
#                            " file and is/are not included in the results below: @ambiguous @notFound.\n\n";
#      print TEXT $badGeneNameMessage;
#   }#end if (@ambiguous || @notFound)

   # Print this first line to the text file
   print TEXT "\nGO slim terms from the $ontologyAspect ontology.\n\n";

   print TAB "GOID\tTERM\tNUM_LIST_ANNOTATIONS\tLIST_SIZE\tCLUSTER_FREQUENCY\tTOTAL_NUM_ANNOTATIONS\tPOPULATION_SIZE\tGENOME_FREQUENCY\tANNOTATED_GENES\n";

   # Print out info of those goids having genes associated with them
   my @totalAnnotatedGenes;
   foreach my $annotation (@annotationsArray){
      my $clusterFreq = ($annotation->{NUM_ANNOTATIONS} / scalar (@genes)) * 100;
      my $clusterFreqValue = sprintf("%.".(2)."f", $clusterFreq);

      my $genomeFreq = ($annotation->{TOTAL_NUM_ANNOTATIONS} / $totalNumGenes) * 100;
      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);
   
      # Keep track if no genes found annotated to the slim terms 
      push(@totalAnnotatedGenes, values (%{$annotation->{ANNOTATED_GENES}}) );

      if (values (%{$annotation->{ANNOTATED_GENES}}) ) {
         print TEXT "TERM\t", $annotation->{TERM}, "\n",
   
                    "GOID\t", $annotation->{GOID}, "\n",

                    "NUM_ANNOTATIONS\t: ", $annotation->{NUM_ANNOTATIONS}, " of ", scalar (@genes), " genes (", $clusterFreqValue,"%)\n",
    
                    "TOTAL_NUM_ANNOTATIONS\t: ", $annotation->{TOTAL_NUM_ANNOTATIONS}," of ", $totalNumGenes, " annotated genes (", $genomeFreqValue,"%)\n",

                    "ANNOTATED_GENES\t: ", join(", ", sort (values (%{$annotation->{ANNOTATED_GENES}}))), "\n\n";
	 print TAB $annotation->{GOID}."\t".$annotation->{TERM}."\t".$annotation->{NUM_ANNOTATIONS}."\t".scalar(@genes)."\t".$clusterFreqValue."%\t".$annotation->{TOTAL_NUM_ANNOTATIONS}."\t".$totalNumGenes."\t".$genomeFreqValue."%\t".join(", ", sort (values (%{$annotation->{ANNOTATED_GENES}})))."\n";
     }
   }

   # Check if no genes found annotated to the slim terms and give
   # appropriate message for text output result page.
   my $noTermFoundMessage = '';
   if (!@totalAnnotatedGenes) {
      # $noTermFoundMessage = "\nNo genes in your input gene list found annotated to GO slim term(s) in the GO slim list from your chosen ".$ontologyAspect.
      #                      " ontology.\n";

      $noTermFoundMessage = "\nNo genes in your input gene list are found annotated to GO slim term(s) in the GO slim list from your chosen ".$ontologyAspect." ontology.\n";   
      print TEXT $noTermFoundMessage;
   }

   # Print out info of those goids havning no genes associated with them.
   foreach my $unannotate_goid (@unannotate_goids) {
      my $missingTerm = $slimGoidsTermsHash{ $unannotate_goid };

      # TOTAL_NUM_ANNOTATIONS (# genes in the genome annotated to this goid)
      my $totalNumAnnotations = $totalNumAnnotationsToGoId{ $unannotate_goid };  #! this can be undefined

      if(!$totalNumAnnotations) { $totalNumAnnotations = 0; }
                       
      my $genomeFreq = ($totalNumAnnotations / $totalNumGenes) * 100;
      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);
       
      print TEXT "TERM\t", $missingTerm, "\n",
                 "GOID\t", $unannotate_goid, "\n",
                 "NUM_ANNOTATIONS\t: 0 of ", scalar (@genes), " genes (0%)\n",
                 "TOTAL_NUM_ANNOTATIONS\t: ",$totalNumAnnotations," of ", $totalNumGenes, " annotated genes (", $genomeFreqValue,"%)\n",
                 "ANNOTATED_GENES\t: none\n\n",
      print TAB $unannotate_goid."\t".$missingTerm."\t0\t".scalar(@genes)."\t0%\t".$totalNumAnnotations."\t".$totalNumGenes."\t".$genomeFreqValue."%\tnone\n";
  }

   close (TEXT);
   close(TAB);

#   system("cp $textFilePath $devTextFilePath");              
}


##############################################################################
sub generateHtmlFile4queryGenes {
##############################################################################
   my ($totalNumGenes, $genesRef, $ambiguousRef, $notFoundRef, $lostRef, $unannotatedRef,
       $annotationsArrayRef, $unannotate_goidsRef,
       $slimGoidsTermsHashRef, $file, $FileNamePID, $outDir, $ontologyAspect,
       $geneUrl, $totalNumAnnotationsToGoIdHashRef) = @_;
   
   #---Dereference referenced variables
   my @genes = @$genesRef;
   my @ambiguous = @$ambiguousRef;
   my @notFound = @$notFoundRef; 
   my @annotationsArray = @$annotationsArrayRef;
   my @unannotate_goids = @$unannotate_goidsRef;
   my %slimGoidsTermsHash = %$slimGoidsTermsHashRef;
   my %totalNumAnnotationsToGoId = %$totalNumAnnotationsToGoIdHashRef;

   my (@annotationRows, @unannotationRows, $clusterFreq, $genomeFreq, $goid, $term, $termLink, $NumAnnotations, $totalNumAnnotations,
       $genomeFreqUse, $genesFreqUse, $annotatedGenes,
       $i, $rowColor,
       @totalAnnotatedGenes
       );

   #---Store rows containing goids having genes associated with them
   #   in @annotationRows for writing to html output file
   $i = 0;
   foreach my $gAnnotation (@annotationsArray){
      $goid = $gAnnotation->{GOID};
      $term = $gAnnotation->{TERM};
      $termLink = "<a target=\"infowin\" href=\"https://www.yeastgenome.org/go/".$goid."\">".$term."</a>";   

      $NumAnnotations = $gAnnotation->{NUM_ANNOTATIONS};
      $clusterFreq = ($gAnnotation->{NUM_ANNOTATIONS} / scalar (@genes)) * 100;
   
      $totalNumAnnotations = $gAnnotation->{TOTAL_NUM_ANNOTATIONS};
      $genomeFreq =  ($gAnnotation->{TOTAL_NUM_ANNOTATIONS} / $totalNumGenes) * 100;
      
      my $clusterFreqValue = sprintf("%.".(2)."f", $clusterFreq);
      $genesFreqUse = $NumAnnotations." of ".scalar (@genes)." genes, ".$clusterFreqValue."%";

      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);
      $genomeFreqUse = $totalNumAnnotations." of ".$totalNumGenes." annotated genes, ".$genomeFreqValue."%";
         
      # keep track if no genes found annotated to the slim terms
      push(@totalAnnotatedGenes, values (%{$gAnnotation->{ANNOTATED_GENES}}) );
   
      my @geneLink;
      foreach my $annotatedGene ( sort (values (%{$gAnnotation->{ANNOTATED_GENES}}) ) ){
	 if ($geneUrl) {
	     my $url = $geneUrl;
	     $url =~ s/<REPLACE_THIS>/$annotatedGene/;
	     my $dbid = $annotation->databaseIdByName($annotatedGene);
	     $url =~ s/<REPLACE_DBID>/$dbid/;
	     my $link = "<a target=\"infowin\" href= \"".$url."\">".$annotatedGene."</a>";
	     push(@geneLink, $link);
	 } else {
	     push(@geneLink, $annotatedGene);
	 }
      }
      $annotatedGenes = join(", ", @geneLink);

      # Work out row color
      if ($i % 2) { $rowColor = "DEB887"; }
      else { $rowColor = "FFE4C4"; }
      
      push(@annotationRows,
           Tr({-bgcolor=>"$rowColor"},
            td({-align=>"left", -nowrap=>''}, $termLink, '(', $goid, ')'),
            td({-align=>"left"}, $annotatedGenes),
            td({-align=>"left", -nowrap=>''}, $genesFreqUse),
            td({-align=>"left", -nowrap=>''}, $genomeFreqUse),
           ),
          );
      
      $i++;
   }

   #---Check if no genes found annotated to the slim terms and give appropriate 
   #   message for search result page later
#   my $noTermFoundMessage = '';

   #---Check if there is/are bad gene name in the gene list
#   my $badGeneNameMessage = '';
#   if (@ambiguous || @notFound) {
#      $badGeneNameMessage = "\nThe following gene(s) is/are not recognized as a valid gene name in ".$annotationFile.
#                            " file and is/are not included in the results below: @ambiguous @notFound.\n";
#   }
   
   #---Store rows containing goids having no genes associated with
   #   them in @unannotationRows for writing to html output file
   foreach my $unannotate_goid (@unannotate_goids) {
      my $missingTerm = $slimGoidsTermsHash{ $unannotate_goid };
            
      $goid = $unannotate_goid;
      $term = $missingTerm;
      $termLink = "<a target=\"infowin\" href=\"https://www.yeastgenome.org/go/".$goid."\">".$term."</a>";

      $NumAnnotations = 0;
      $clusterFreq = 0;

#      select(STDERR); $| = 1; select(STDOUT);
      #TOTAL_NUM_ANNOTATIONS (# genes in the genome annotated to this goid)
      $totalNumAnnotations = $totalNumAnnotationsToGoId{ $unannotate_goid };
      my $genomeFreq = ($totalNumAnnotations / $totalNumGenes) * 100;
      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);

      $genesFreqUse = $NumAnnotations." of ".scalar (@genes)." genes, ".$clusterFreq."%";
      if (!$totalNumAnnotations) { $totalNumAnnotations = 0; }
      $genomeFreqUse = $totalNumAnnotations." of ".$totalNumGenes." annotated genes, ".$genomeFreqValue."%";

      $annotatedGenes = 'none';
      
      # Work out row color
      if ($i % 2) { $rowColor = "DEB887"; }
      else { $rowColor = "FFE4C4"; }
      
      push(@unannotationRows,
           Tr({-bgcolor=>"$rowColor"},
            td({-align=>"left", -nowrap=>''}, $termLink, '(', $goid, ')' ),
            td({-align=>"left"}, $annotatedGenes),
            td({-align=>"left", -nowrap=>''}, $genesFreqUse),
            td({-align=>"left", -nowrap=>''}, $genomeFreqUse),
           ),#end Tr
          );
        $i++;
   }

   #---Work out the name of html file
   my $htmlFile = $FileNamePID.$file;
   # Delete anything up to and including the last slash
   $htmlFile =~ s/.*\///;
   # Delete anything following the last period
   $htmlFile =~ s/\..*//;
   # Now add an terms suffix
   $htmlFile .= "_slimTerms.html";
   my $htmlFilePath = $outDir.$htmlFile;
   $DEBUG && print "htmlFilePath: $htmlFilePath\n";
      
   #---Open html file to write
   open (HTML, ">$htmlFilePath") || die "$htmlFilePath exists, cannot overwrite it: $!";

   #---Generate html output file      
   print HTML "<html><body>\n";
   
   # if user choose email his/her results, print this to html table output file
   if ($email) {

      if ($opt_s) {
      
        print HTML "<font color=red>PLEASE NOTE: </font>",$GoSlimTermsOption,$GoSlimTermsNotice, "<br>".$userGoSlimTermWarning."<br>\n"; 
      }
      else {

         print HTML "<font color=red>PLEASE NOTE: </font>",$GoSlimTermsOption,"<br>\n";
      }
      
      print HTML "<center><b>Save Options: </b>", $htmlTableLink, " | ", $plainTextLink, "</center>\n"; 
#      print HTML "<center>", $inputDataLink, $inputGenesNum, " | ", $userGoSlimListLink, " | ", "</center>\n"; 
      print HTML "<center>", $inputDataLink, " | ", $userGoSlimListLink, " | ", "</center>\n"; 
      print HTML "<b>",$entryMissingGoidMesg, "</b><br>\n";
   }            

       # print HTML "<br><b>Your input list contains ",$#inputGenes+1," genes.</b><br>";
       if (@inputDuplicates) {
	   print HTML "<br><b>These ",$#inputDuplicates+1," identifier(s) are duplicated in your input list:</b> ", join(" ", @inputDuplicates),"<br>";
       }
       if (@ambiguous) {
	   print HTML "<br><b>These ",$#ambiguous+1," identifier(s) are found to be ambiguous:</b> ", join(" ", @ambiguous),"<br>";
       }
       if (@notFound) {
	   # print HTML "<br><b>These ",$#notFound+1," identifier(s) are found to be unannotated:</b> ", join(" ", @notFound), "<br>";
	   print HTML "<br><b>These ",$#notFound+1," identifier(s) represent either invalid gene names, dubious ORFs unlikely to encode functional proteins or genes which are currently unannotated:</b> ", join(" ", @notFound), "<br>"; 
       }
       if (@{$lostRef}) {
	   print HTML "<br><b>These ",$#{$lostRef}+1, " identifier(s) are not annotated in the slim, but they had non-root annotations that are not in the slim:</b> ", join(" ", @{$lostRef}), "<br>";
       }
       if (@{$unannotatedRef}) {
	   # print HTML "<br><b>These ",$#{$unannotatedRef}+1, " identifiers had no non-root annotations:</b> ", join(" ", @{$unannotatedRef}),"<br>";
	   print HTML "<br><b>These ",$#{$unannotatedRef}+1, " identifier(s) represent valid gene names that either could not be mapped to terms in the current GO slim set or are currently annotated to the root node for the slim set being used:</b> ", join(" ", @{$unannotatedRef}),"<br>";
       }
#      if ($badGeneNameMessage) {
#         print HTML "<b>", "$badGeneNameMessage", "</b>"."<br>"."<br>";
#      }#end if ($badGeneNameMessage) 

   if (!@totalAnnotatedGenes) {
       print HTML "<br><font color=red><b>No genes in your input gene list found annotated to GO slim term(s) in the GO slim list from your chosen ".$ontologyAspect." ontology.</b></font><br>";
   } else {
      print HTML "<center>\n",
                 "<table border=0 cellpadding=2>\n",
                 "<tr align=center>\n",
                     "<td colspan=5><b>","GO Terms from the $ontologyAspect Ontology","</b></td>",
                 "</tr>\n",
                 "<tr bgcolor=#993300>\n",
                      "<th align=center nowrap><font color=#FFFFFF>GO Term (GO ID)</font></th>\n",
                      "<th align=center><font color=#FFFFFF>Genes Annotated to the GO Term</font></th>\n",
                      "<th align=center><font color=#FFFFFF>GO Term Usage in Gene List</font></th>\n",
                      "<th align=center><font color=#FFFFFF>Genome Frequency of Use</font></th>\n",
                 "</tr>\n";
   
      print HTML "@annotationRows";
      
      print HTML "@unannotationRows";
   
      print HTML "</table>\n",
               "</center>\n";  
   }

   # make sure this is in a line by itself
   print HTML "\n</body></html>";
            
   close(HTML);

#   system("cp $htmlFilePath $devHtmlFilePath");

}


##############################################################################
sub validateFile {
##############################################################################
   my($file) = @_;
   my $errorMessage;
   #---check wether the file exists
   if (!(-e $file)) {
      $errorMessage = "The file $file you entered does not exist.\n";
      &printErrorMessage($errorMessage);
   }
}


##############################################################################
sub allGoids4slimOntologyFile {
##############################################################################
   my ($ontologyUnparsedFile, $ontologyAspect) = @_;
   
   #---Get goids for the specified aspect in the slim ontology file
   # Open the slim ontology file to read line by line
   open (SLIMONTOLOGYFILE , "$ontologyUnparsedFile") || die ("Cannot create $ontologyUnparsedFile : $!");

   # This hash contains all goids and their associated terms (i.e. Key
   # = goid, value = term) for the specifed aspect in the slim ontology
   # file.
   my %slimGoidsTermsHash; 

   while (my $line = <SLIMONTOLOGYFILE>) {
       if ($line =~ /\[Term\]/) {
	   my ($goid, $name, $aspect);
	   while ($line = <SLIMONTOLOGYFILE>) {
	       chomp($line);
	       if ($line =~ /^id:\s*(GO:\d+)(\s|$)/) {
		   $goid = $1;
	       } elsif ($line =~ /^name:\s*(.*)$/) {
		   $name = $1;
	       } elsif ($line =~ /^namespace:\s*$ontologyAspect/) {
		   $aspect = $ontologyAspect;
	       } elsif ($line =~ /^\s*$/) {
		   last;
	       }
	   }
	   if ($goid && $name && $aspect) {
	       $slimGoidsTermsHash{$goid} = $name;
	   }
       } elsif ($line =~ /\[Typedef\]/) {
	   last;
       }
   }
   
   close (SLIMONTOLOGYFILE);

   return (\%slimGoidsTermsHash);
}


##############################################################################
sub totalNumAnnotationsToGoId { 
##############################################################################
   my ($annotation, $aspect, $databaseIdsArrayRef) = @_;

   #---This hash has key = goid, value = # annotation to the goid
   my %totalNumAnnotationsToGoId; 

   #---Use databaseId to get goids. Then use goids to get #
   #   annotations associated with each goid.
   foreach my $databaseId (@{$databaseIdsArrayRef}) {
      # Get all goids associated with this databaseId
      my $goidsArrayRef = $annotation->goIdsByDatabaseId(databaseId => $databaseId,
                                                         aspect     => $aspect);

      # For each goid for this databaseId, record this goid and its ancestor goids
      my %goids;
      foreach my $goid (@{$goidsArrayRef}) {

         if(!$ontology->nodeFromId($goid)) 
         { next; }

         $goids{$goid} = undef;

         foreach my $ancestor ($ontology->nodeFromId($goid)->ancestors) {
            $goids{$ancestor->goid} = undef;
         }
      }
      my @goids = keys (%goids);

      # For this databaseId's goid and its ancestor goids, count #
      # annotations associated with each goid.
      foreach my $goid (@goids) {
         $goid =~ s/\s+//g;
         $totalNumAnnotationsToGoId{ $goid }++;
      }

   }

   return (\%totalNumAnnotationsToGoId);  
}


##############################################################################
sub findSlimTerms {
##############################################################################
   my ($ontology, $annotation, $aspect, $databaseIdsArrayRef, $slimGoidsTermsHashRef, $totalNumAnnotationsToGoIdHashRef) = @_;
   
   #---Dereference referenced variables
   my %slimGoidsTermsHash = %$slimGoidsTermsHashRef;
   my %totalNumAnnotationsToGoId = %$totalNumAnnotationsToGoIdHashRef;

   #---This hash has key = goid, value = # annotations to the goid
   my %totalNodeCounts; 

   #---Use databaseId to get goids. Then use goids to get #annotations
   #   associated with each goid
   foreach my $databaseId (@{$databaseIdsArrayRef}) {
      # Get all goids associated with this databaseId
      my $goidsArrayRef = $annotation->goIdsByDatabaseId(databaseId => $databaseId,
                                                         aspect     => $aspect);

      # For each goid associated with this databaseID, record this
      # goid and its ancestor goids.
      my %goids;
      foreach my $goid (@{$goidsArrayRef}) {
         
         if(!$ontology->nodeFromId($goid))
         { next; }

         $goids{$goid} = undef;

         foreach my $ancestor ($ontology->nodeFromId($goid)->ancestors) {
            $goids{$ancestor->goid} = undef;
         }
      }
      my @goids = keys (%goids);
       
      # For this databaseId's goid and its ancestor goids, count #
      # annotations for each goid.
      foreach my $goid (@goids) {
         $goid =~ s/\s+//g;
         $totalNodeCounts{ $goid }++;
      }

   }

   #---Keep track of GOID, TERM, NUM_ANNOTATIONs,and
   #   TOTAL_NUM_ANNOTATIONS for each goid for later printing
   my ($x, $M, $hashRef, @annotationsArray, $GOID, $TERM);
   foreach my $goid (keys(%totalNodeCounts)) {
      # Interested in GO slim terms (internal nodes of GO tree) only.  NOT interested in GO terms corresponding to 
      # GO:0003673:Gene_Ontology (the root node of GO tree) and ontology aspects (immediate children of the root node) 
      # like GO:0008150:biological_process, GO:0003674:molecular_function, and GO:0005575:cellular_component.  
      if ($goid ne 'GO:0008150' && $goid ne 'GO:0003674' && $goid ne 'GO:0005575' &&  $goid ne 'GO:0003673') {
         $x = $totalNodeCounts { $goid };
         $M = $totalNumAnnotationsToGoId { $goid }; 
         $GOID = $goid;
         $TERM = $slimGoidsTermsHash{ $goid };
         
         # Add following if (!$TERM) to deal with user inputs just GOID for 'advanced options' in GO Term Mapper web tool      
         if (!$TERM) {
	     if (!$fullOntology) {
		 $fullOntology = GO::OntologyProvider::OboParser->new(ontologyFile=>"/var/www/data/gene_ontology.obo", aspect => $aspect);
	     }
            my $node = $fullOntology->nodeFromId($GOID);
            $TERM = $node->term;            
         }

         # Put the GOID, TERM, NUM_ANNOTATIONS, and
         # TOTAL_NUM_ANNOTATIONS for each goid into a hashRef.
         $hashRef = {
                     GOID => $GOID,
                     TERM => $TERM,
                     NUM_ANNOTATIONS => $x,
                     TOTAL_NUM_ANNOTATIONS => $M,
                    };

         # @annotationsArray contains references of the hashRef(s)
         # (i.e. references of references to hash of GOID, TERM,
         # NUM_ANNOTATIONS and TOTAL_NUM_ANNOTATIONS for each goid).
         push (@annotationsArray, $hashRef);

      }
   }


   #---Now sort the @annotationsArray
   # If genome query, sort the @annotationsArray by TOTAL_NUM_ANNOTATIONS
   if (!@ARGV) {
      @annotationsArray = sort { $b->{TOTAL_NUM_ANNOTATIONS} <=> $a->{TOTAL_NUM_ANNOTATIONS} } @annotationsArray;
   }
   # If genes query, sort the @annotationsArray by NUM_ANNOTATIONS
   if (@ARGV) {
      @annotationsArray = sort { $b->{NUM_ANNOTATIONS} <=> $a->{NUM_ANNOTATIONS} } @annotationsArray;
   }


   #---START DEALING WITH THOSE GOIDS HAVING NO GENES ASSOCIATED WITH THEM.
   # NOW DEAL WITH THOSE GOIDS IN SLIM ONTOLOGY FILE FOR THE SPECIFIED
   # ASPECT HAVING NO GENES IN THE GENOME ASSOCIATED WITH THEM.
   my ($unannotate_goidsArrayRef) = getUnannotatedGoids(\%totalNodeCounts, $slimGoidsTermsHashRef); 

   # @annotationsArray contains goids having genes associated with them.
   # $unannotate_goidsArrayRef is referece to an array of goids having
   # no genes associated with them.
   return (\@annotationsArray, $unannotate_goidsArrayRef);
}


##############################################################################
sub getUnannotatedGoids {
##############################################################################
   my ($totalNodeCountsHashRef, $slimGoidsTermsHashRef) = @_;

   #---Get goids in slim ontology file having no genes associated with them.
   my (@unannotate_goids);

   # Search each goid in the slim ontology file against the list of
   # all annotated goids, if this goid is not found in the list of
   # annotated goids, put it in the @unannotate_goids arrray.
   foreach my $goid( keys(%{$slimGoidsTermsHashRef}) ) { #foreach goid in the slim ontology file
      chomp($goid);
      $goid =~ s/\s+//g;

      my $found_unannotateGoid = 0;
      foreach my $annotateGoid ( keys(%{$totalNodeCountsHashRef}) ){   

         if ($goid eq "$annotateGoid") { 
            $found_unannotateGoid = 1;  
            last; 
         }
      }
      if ($found_unannotateGoid == 0) { 
         push (@unannotate_goids, $goid); 
      }
   }

   # @unannotate_goids contains unannotated goid found in slim ontology file.
   return (\@unannotate_goids);  
    
}


##############################################################################
sub generateTextFile {
##############################################################################
   my ($annotationsArrayRef, $totalNumGenes, $unannotate_goidsRef, $slimGoidsTermsHashRef,
       $FileNamePID, $annotationFile, $outDir, $ontologyAspect)  = @_;

   #---Dereference referenced variables
   my @annotationsArray = @$annotationsArrayRef;
   my @unannotate_goids = @$unannotate_goidsRef;
   my %slimGoidsTermsHash = %$slimGoidsTermsHashRef;

   #---Work out the name of text file
   my $textFile = $FileNamePID.$annotationFile."_slimTerms.txt";
   my $textFilePath = $outDir.$textFile;
   $DEBUG && print "TextFilePath: $textFilePath\n";

   #---Open the text file to write
   open(TEXT, ">$textFilePath") or die "$textFilePath file exists, cannot overwrite it: $!\n";

   #---Print this first line to the text file
   print TEXT "GO slim terms from the $ontologyAspect ontology.\n\n";

   $DEBUG && print "Write GOTermMapper result to text file ...\n";   
   #---Print out info of those goids having genes associated with them 
   foreach my $annotation (@annotationsArray) {
      my $genomeFreq = ($annotation->{TOTAL_NUM_ANNOTATIONS} / $totalNumGenes) * 100;
      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);
   
      print TEXT "TERM\t", $annotation->{TERM}, "\n",
                 "GOID\t", $annotation->{GOID}, "\n",  
                 "TOTAL_NUM_ANNOTATIONS\t", $annotation->{TOTAL_NUM_ANNOTATIONS}," of $totalNumGenes ($genomeFreqValue", "%) in the genome\n\n";
   }

   #---Print out info of those goids having no genes associated with them 
   foreach my $unannotate_goid (@unannotate_goids) {
      my $missingTerm = $slimGoidsTermsHash{ $unannotate_goid };

      print TEXT "TERM\t", $missingTerm, "\n",
                 "GOID\t", '|'.$unannotate_goid.'|', "\n",
                 "TOTAL_NUM_ANNOTATIONS\t", "0 of $totalNumGenes (0%) in the genome\n\n";
   }

   close (TEXT);

#   system("cp $textFilePath $devTextFilePath");

   return ($textFile);
}


##############################################################################
sub generateHtmlFile {
##############################################################################
   my ($annotationsArrayRef, $totalNumGenes, $unannotate_goidsRef, $slimGoidsTermsHashRef,
       $FileNamePID, $annotationFile, $outDir, $ontologyAspect) = @_;

   #---Dereference referenced variables
   my @annotationsArray = @$annotationsArrayRef;
   my @unannotate_goids = @$unannotate_goidsRef;
   my %slimGoidsTermsHash = %$slimGoidsTermsHashRef;


   my (@annotationRows, @unannotationRows, $genomeFreq, $goid, $term, $termLink, $totalNumAnnotations, $genomeFreqUse,
       $i, $rowColor);
   #---Store rows containing those goids having genes associated with
   #   them in @annotationRows for writing to html output file
   $i = 0;
   foreach my $annotation (@annotationsArray) {
      $goid = $annotation->{GOID};
      $term = $annotation->{TERM};
      $termLink = "<a target=\"infowin\" href=\"https://www.yeastgenome.org/go/".$goid."\">".$term."</a>";

      $totalNumAnnotations = $annotation->{TOTAL_NUM_ANNOTATIONS};

      $genomeFreq = ($annotation->{TOTAL_NUM_ANNOTATIONS} / $totalNumGenes) * 100;
      my $genomeFreqValue = sprintf("%.".(2)."f", $genomeFreq);
      
      $genomeFreqUse = $totalNumAnnotations." of ".$totalNumGenes." annotated genes, ".$genomeFreqValue."%";

      # Work out row color
      if ($i % 2) { $rowColor = "DEB887"; }
      else { $rowColor = "FFE4C4"; }
       
      push(@annotationRows, 
           Tr({-bgcolor=>"$rowColor"}, 
            td({-align=>"left", -nowrap=>''}, $termLink, '(', $goid, ')' ),
            td({-align=>"left", -nowrap=>''}, $genomeFreqUse),
           ),#end Tr
 
          );
 
     $i++;
   }

   #---Store rows containing those goids having no genes associated
   #   with them in @unannotationRows for writing to html output file.
   foreach my $unannotate_goid (@unannotate_goids) {
      my $missingTerm = $slimGoidsTermsHash{ $unannotate_goid };

      $goid = $unannotate_goid;
      $term = $missingTerm;
      $termLink = "<a target=\"infowin\" href=\"https://www.yeastgenome.org/go/".$goid."\">".$term."</a>";

      $totalNumAnnotations = 0;
      $genomeFreq = 0;
      $genomeFreqUse = $totalNumAnnotations." of ".$totalNumGenes." annotated genes, ".$genomeFreq."%";

      # Work out row color
      if ($i % 2) { $rowColor = "DEB887"; }
      else { $rowColor = "FFE4C4"; }

      push(@unannotationRows,
           Tr({-bgcolor=>"$rowColor"},
            td({-align=>"left", -nowrap=>''}, $termLink, '(', $goid, ')' ),
            #td({-align=>"left", -nowrap}, $goid),
            td({-align=>"left", -nowrap=>''}, $genomeFreqUse),
	   ),
	  );

       $i++;
   }

   #---Work out name of html file
   my $htmlFile = $FileNamePID.$annotationFile."_slimTerms.html";
   my $htmlFilePath = $outDir.$htmlFile;
   $DEBUG && print "htmlFilePath: $htmlFilePath\n";
   
   #---Open html file to write 
   open (HTML, ">$htmlFilePath") || die "cannot create $htmlFilePath: $!";

   #---Generate html output file
   print HTML "<html><body>\n";
   print HTML br, "\n";
  
   # if user choose email his/her results, print this to html table output file
   if ($email) {

      if ($opt_s) {
      
        print HTML "<font color=red>PLEASE NOTE: </font>",$GoSlimTermsOption,$GoSlimTermsNotice,"<br>".$userGoSlimTermWarning."<br>\n"; 
        
      }
      else {

         print HTML "<font color=red>PLEASE NOTE: </font>",$GoSlimTermsOption,"<br>\n";
     }

     print HTML "<center><b>Save Options: </b>", $htmlTableLink, " | ", $plainTextLink, "</center>\n";
     print HTML "<center>", " | ", $userGoSlimListLink, " | ", "</center>\n";
     print HTML "<b>",$entryMissingGoidMesg, "</b><br><br>\n";  

   }


   print HTML "<center>\n",
              "<table border=0 cellpadding=2>\n",
              "<tr align=center>\n",
                  "<td colspan=3><b>","GO Slim Terms from the $ontologyAspect Ontology","</b></td>",
              "</tr>\n",    
              "<tr bgcolor=#993300>\n",
                  "<th align=center nowrap><font color=#FFFFFF>GO Slim Term (GO ID)</font></th>\n",
                  "<th align=center><font color=#FFFFFF>Genome Frequency of Use</font></th>\n",
              "</tr>\n";
 
    print HTML "@annotationRows";

    print HTML "@unannotationRows";

    print HTML "</table>\n",
               "</center>\n";
              
   print HTML "</body></html>";
   
   close(HTML);

#   system("cp $htmlFilePath $devHtmlFilePath");  

}


##############################################################################
sub validateDir {
##############################################################################
   my ($outDir, $goDir, $goParseDir) = @_;
   #---Validate if directory where various output files written to exists
   if ($outDir) {
       opendir (DIR, $outDir) or die("The directory $outDir you entered does not exist: $!");
       closedir (DIR);
   }
   #---Validate if directory where GO slim files locate exists
   elsif ($goDir) {
       opendir (DIR, $goDir) or die("The directory $goDir you entered does not exist: $!");
       closedir (DIR);
   } 
   #---Validate if directory where preparsed GO slim files locate exists
   elsif ($goParseDir) {
       opendir (DIR, $goParseDir) or die("The directory $goParseDir you entered does not exist: $!");
       closedir (DIR);
   }

   #---Validate if directory where GO files downloaded from GO ftp site locate exists
#   elsif ($GOdir) {
#       opendir (DIR, $GOdir) or die("The directory $GOdir you entered does not exist: $!");
#       closedir (DIR);
#   }
}


##############################################################################
sub getOntologyAspectInfo { 
##############################################################################
   my ($aspect) = @_;
   
   my %ontologyAspect = ( P => 'biological process',
                          F => 'molecular function',
                          C => 'cellular component'
			  );

   if (exists ($ontologyAspect { $aspect }) ) {
       return (1, $ontologyAspect { $aspect });
   } else {
       return (0, $ontologyAspect { $aspect });
   } 
}


##############################################################################
sub validateAspect {
##############################################################################
   my($aspectExist) = @_;

   my $errorMessage;

   #---validate ontology aspect argument
   if ($aspectExist == 0) {
      $errorMessage = "The ontology aspect $aspect you entered is invalid.  ".
                      "The valid ontology aspect is :F, C or P\n";
      &printErrorMessage($errorMessage);
   }
}


##############################################################################
sub validateGeneAsscFile {
##############################################################################
   my($annotationFile) = @_;
   my $errorMessage;

   my ($organismFileExist) = $metaData->organismFileExist($annotationFile);
   # if it's a custom annotation file it won't be known -- mark
   if (($organismFileExist == 0) && (($annotationFile !~ /\//) || (! -f $annotationFile))) {
      $errorMessage = "The $annotationFile you entered is invalid ".
                      "GO gene-annotation file\n";
      &printErrorMessage($errorMessage);
   }

}


##############################################################################
sub printErrorMessage {
##############################################################################
   my ($errorMessage) = @_;

   print "$errorMessage";
   exit;
}


sub sendEmail {
    
  #my ($sendmail, $date, $email, $contactEmailAddress, $GOTermMapperResultsUrl) = @_;
    
   my ($inputGeneListErrorMessage) = @_;

   my $subject = "GO Term Mapper Results";

   my $emailMesg;
   if ($inputGeneListErrorMessage =~ m/No known genes exist/) {
         
      $emailMesg = "No result generated for the GO Term Mapper you submitted on $date due to :\n\n". 
                   $inputGeneListErrorMessage;    
   }    
   else {
          
      $emailMesg = "Results of GO Term Mapper you submitted on $date can be viewed at:\n\n".
                  $GOTermMapperResultsUrl.
                  "\n\n***PLEASE NOTE THAT THE RESULTS WILL BE REMOVED FROM OUR SYSTEM AFTER A WEEK***\n";  
    }

    open(MAIL, "| $sendmail") or die "Could not open sendmail: ";
    
   print MAIL <<EOF;
From: $contactEmailAddress 
To: $email
Subject: $subject

$emailMesg


EOF
   close MAIL;

}



##############################################################################
#  PLAIN OLD DOCUMENTATION SECTION
#
##############################################################################
__END__

=pod

=head1 NAME

GOTermMapper.pl - maps the granular GO annotations for genes in a list to a set of broader, high-level parent GO slim terms.
 

=head1 SYNOPSIS

GOTermMapper.pl bins the submitted gene list to a static set of ancestor GO terms according to the user specified GO slim file for 
the specified ontology aspect (P, F, or C) and gene-association file, and outputs result file in plain text format by default, or in 
html table format if the user chooses html output file format option.

The user can get help message of how to use the program by issuing the command: perl B<GOTermMapper.pl> B<-H>,
and the program's complete POD (plain old documentation) by issuing the command: perl B<GOTermMapper.pl> B<-M>.

Usages:

(1) To bin the genes of a genome to GO slim terms in the user specified GO slim file:

    Usage:

    perl B<GOTermMapper.pl> B<-a> I<ontology aspect>
                            B<-o> I<GO slim file>
                            B<-g> I<gene-association file>

    Usage example:

    perl B<GOTermMapper.pl> B<-a> C B<-o> goslim_yeast.2003 B<-g> gene_association.sgd


(2) To bin the list of genes of an organism to GO slim terms in the user specified GO slim file:

    Usage:

    perl B<GOTermMapper.pl> B<-a> I<ontology aspect>
                            B<-o> I<GO slim file>
                            B<-g> I<gene-association file>
                            I<file1> I<file2> I<file3> ... I<fileN>

    Usage example:

    e.g: perl GOTermMapper.pl B<-a> C B<-o> goslim_yeast.2003 B<-g> gene_association.sgd genes.txt


=head1 OPTIONS

All following options, except those marked '(REQUIRED)', are OPTIONAL to the program.

=over 4

=item B<-a> I<ontology aspect (P, F, or C)> (REQUIRED)

Ontology aspect is I<ontology aspect (P, F, or C)>. The user is
REQUIRED to use B<-a> switch to specify the program required ontology
aspect.

e.g: perl B<GOTermMapper.pl> B<-a> C -o goslim_yeast.2003 -g gene_association.sgd

=item B<-o> I<GO slim file from GO consortium> (REQUIRED)

Name of the GO slim file is I<GO slim file>.  The user is REQUIRED to
use B<-o> switch to specify the program required GO slim file.

e.g: perl B<GOTermMapper.pl> -a C B<-o> goslim_yeast.2003 -g gene_association.sgd

=item B<-g> I<gene-associaton file> (REQUIRED)

Name of gene-association file is I<gene-associaton file>.  The user is REQUIRED to use  B<-g> switch to 
specify the program required gene-association file.

e.g: perl B<GOTermMapper.pl> -a C -o goslim_yeast.2003 B<-g> gene_association.sgd

=item B<-s> I<GO slim file from user>

Name of the GO slim file is I<user GO slim file>.  Use  B<-s> switch to specify user's customized GO slim file.
The user specified GO slim file is placed in the '/tmp' directory.  For web-based GO Term Mapper cgi, the user 
specified GO slim file is uploaded to the '/www/tmp/' directory.

e.g: perl GOTermMapper.pl -a C B<-s> goslim_yeast.xxx -g gene_association.sgd

=item B<-d> I<directory>

I<directory> where various output files containing the results of the GO Term Mapper are written to.

e.g: perl GOTermMapper.pl B<-d> '/tmp/' -a C -o goslim_yeast.2003 -g gene_association.sgd 

=item B<-G> I<directory>

I<directory> where the GO slim files from GO consortium and gene-association slim files locate.

e.g: perl GOTermMapper.pl B<-G> '/Genomics/GO/data/unparsed_slim/' -a C -o goslim_yeast.2003 -g gene_association.sgd

=item B<-P> I<directory>

I<directory> where the parsed GO slim files and parsed gene-association slim files locate.

e.g: perl GOTermMapper.pl B<-P> '/Genomics/GO/data/parsed_slim/' -a C -o goslim_yeast.2003 -g gene_association.sgd

=item B<-D> I<directory>

I<directory> where the GO files and gene-association files downloaded from the GO ftp site locate.

e.g: perl GOTermMapper.pl B<-D> '/Genomics/GO/data/unparsed/' -a C -o goslim_yeast.2003 -g gene_association.sgd

=item B<-p> I<map2slim program path>

I<map2slim program path> where the map2slim program locates.

e.g: perl GOTermMapper.pl B<-p> '/Genomics/GO/bin/map2slim' -a C -s goslim_yeast.xxx -g gene_association.sgd

=item B<-h>

Output file is a html table.  Use B<-h> switch to specify program output file containing html table.

e.g: perl GOTermMapper.pl B<-h> -a C -o goslim_yeast.2003 -g gene_association.sgd 

=item B<-u> I<genome's gene url>

The URL for displaying information known about a gene in the genome is I<genome's gene url>.   Use B<-u> switch to 
overwrite the program default gene url for displaying information known about a gene within a genome.

e.g: perl GOTermMapper.pl B<-u> 'https://www.yeastgenome.org/locus/' -a C -o goslim_yeast.2003 -g gene_association.sgd

The program default gene url(s) known for the genomes as of April 2004 are listed below:

            Compugen_UniProt         - http://www.pir.uniprot.org/cgi-bin/upEntry?id=
            GeneDB_Lmajor            - http://www.genedb.org/genedb/Search?organism=leish&name=
            GeneDB_Pfalciparum       - http://www.genedb.org/genedb/Search?organism=malaria&name=
            GeneDB_Tbrucei           - http://www.genedb.org/genedb/Search?organism=tryp&name=
            Dictyostelium discoideum - http://dictybase.org/db/cgi-bin/dictyBase/locus.pl?locus=
            Drosophila melanogaster  - http://flybase.bio.indiana.edu/.bin/fbidq.html?FBgn
            homo sapien              - http://www.ensembl.org/Homo_sapiens/geneview?gene=
            Oryza sativa             - http://www.gramene.org/perl/protein_search?acc=
            Mus musculus             - http://www.informatics.jax.org/searches/accession_report.cgi?id=
            Rattus norvegicus        - http://rgd.mcw.edu/tools/genes/genes_view.cgi?id=
            Saccharomyces Cerevisiae - https:/www.yeastgenome.org/locus/
            Arabidopsis thaliana     - http://arabidopsis.org/servlets/TairObject?accession=gene:
            Caenorhabditis elegans   - http://www.wormbase.org/db/gene/gene?name=
            Danio rerio              - http://zfin.org/cgi-bin/webdriver?MIval=aa-markerview.apg&OID=
            TIGR Geobacter sulfurreducens PCA - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
            TIGR Pseudomonas syringae DC3000  - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
            TIGR Trypanosoma brucei chr2      - http://www.tigr.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db=tba1&orf=
            TIGR Bacillus anthracis           - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
            TIGR Arabidopsis thaliana         - http://www.tigr.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db=ath1&orf=
            TIGR Coxiella bumetii             - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
            TIGR Shewanella oneidensis        - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
            TIGR Vibrio cholerae              - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=



=item B<-f> I<user specified file concatenator>

Name of the output file concatenator is I<user specifier file concatenator>.  Use  B<-s> switch to specify output file concatenator.

e.g: perl GOTermMapper.pl -a C -o goslim_yeast.2003 -g gene_association.sgd B<-f> sgd17Sept04

=item I<file1> I<file2> ... I<fileN>

After any of the program switches, I<file1> I<file2> ... I<fileN> is one file or a number of 
files (each contains list of genes) the user enters. 

e.g: perl GOTermMapper.pl -a C -o goslim_yeast.2003 -g gene_association.sgd B<genes.txt>

=back


All following options are used by the program to send GO Term Mapper results to user:

=over 4

=item B<-e> I<email address>

I<email address> used by the program to email the user the GO Term Mapper results.  Use B<-e> 
switch to provide email address to the program.

e.g: perl GOTermMapper.pl -a C -o goslim_yeast.2003 -g gene_association.sgd B<-e> 'lmcmahan@genomics.princeton.edu'

=item B<-U> I<GO Term Mapper results' url>

The URL for displaying the GO Term Mapper results on the web is I<GO Term Mapper results' url>.  
Use B<-U> switch to overwrite the program default 'http://go.princeton.edu/tmp/' URL of the GO 
Term Mapper results.

e.g: perl GOTermMapper.pl -a C -o goslim_yeast.2003 -g gene_association.sgd B<-f> sgd17Sept04 B<-U> 'http://go.princeton.edu:8080/tmp/sgd17Sept04_association.sgd_slimTerms.html'

=item B<-i> I<input gene list's url>

The URL for displaying the user's input gene list on the web is I<input gene list's url>.  Use 
B<-i> switch to overwrite the program default 'http://go.princeton.edu/tmp/' URL of the user's 
input gene list.

e.g: perl GOTermMapper.pl -a C -o goslim_yeast.2003 -g gene_association.sgd B<-f> sgd17Sept04 B<-i> 'http://go.princeton.edu:8080/tmp/sgd17Sept04.txt' 

=item B<-O> I<GoSlimTermsOption>

Note, obtained from the GO Term Mapper CGI script, to be displayed on the GO Term Mapper result 
web page is I<GoSlimTermsOption>, indicating the option the user has chosen to supply his/her list 
of GO slim terms to the program.

=item B<-W> I<userGoSlimTermWarning>

Note, obtained from the GO Term Mapper CGI script, to be displayed on the GO Term Mapper result 
web page is I<userGoSlimTermWarning>, warning the user that he/she has supplied more than one list 
of GO slim terms to the program,and that the program returns results ONLY for ONE supplied GO slim 
list. 

=item B<-T> I<htmlTableLink>

Relative path to the GO Term Mapper result html table, obtained from the GO Term Mapper CGI script, is I<htmlTableLink>.  The program default relative path of the GO Term Mapper result html table 
is 'tmp'.   

=item B<-t> I<plainTextLink>

Relative path to the GO Term Mapper result plain text file, obtained from the GO Term Mapper CGI 
script, is I<plainTextLink>.  The program default relative path of the GO Term Mapper result 
plain text file is 'tmp'. 

=item B<-I> I<inputDatatLink>

Relative path to the file of user input gene list, obtained from the GO Term Mapper CGI script, is 
I<inputDatatLink>.  The program default relative path of the user input gene list file is 'tmp'. 

=item B<-n> I<inputGenesNum>

The total number of genes in the user input gene list, obtained from the GO Term Mapper CGI script, is I<inputGenesNum>.

=item B<-S> I<userGoSlimListLink>

Relative path to the file of user supplied list of GO slim terms, obtained from the GO Term Mapper 
CGI script, is I<userGoSlimListLink>.  The program default relative path of the user supplied GO 
slim list is 'tmp'.

=item B<-E> I<entryMissingGoidMesg>

Note, obtained from the GO Term Mapper CGI script, to be displayed on the GO Term Mapper result 
web page is I<entryMissingGoidMesg>, indicating the entries in the user supplied GO slim list 
containing no GOIDs and they are not included in the GO Term Mapper results.

=item B<-w> I<GO projects' web server url>

The web server URL of the GO projects, obtained from the GO Term Mapper CGI script, is 
I<GO projects' web server url>.  The program default URL of the GO projects is 
'http://go.princeton.edu'  

=item B<-H>

Print help message to the screen.

e.g: perl B<GOTermMapper.pl> B<-H>

=item B<-M>

Print complete POD (plain old documentation) to the screen.

e.g: perl B< GOTermMapper.pl> B<-M>

=back

=head1 AUTHOR

Linda McMahan, lmcmahan@genomics.princeton.edu

=cut

