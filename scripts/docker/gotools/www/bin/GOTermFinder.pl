#!/usr/bin/perl
# Copyright (c) 2004 Lewis-Sigler Institute, Princeton University
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated files, libraries,
# and modules (collectively termed the "Software"), to use the Software
# without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software
# is furnished to do so, subject to the following conditions:
#
# 1. The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# 2. The Software may include modified versions of certain libraries
# and modules which include their own license terms and copyrights.
# The modified files are still subject to their original license terms.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# PORTING
#
# Change the "use lib" paths below to point to your installation of the modified GO libraries.
# Change the $goDir and, optionally, the $goParseDir paths, or use -g with an absolute path, or use -d and -o.
# Optionally change the GO View config file in $confFile.

##############################################################################
# PROGRAM NAME: GOTermFinder.pl
# DATE CREATED: March 2004 (L McMahan)
# AUTHORS: Mark Schroeder <mark@genomics.princeton.edu>, Linda McMahan <lmcmahan@genomics.princeton.edu>
# COMMAND: ./GOTermFinder.pl [-d <GO and gene annotation files directory>]
#                            [-o <parsed/cached object files directory>]
#                             -t <output directory> 
#                             -a <ontology aspect> 
#                             -g <gene annotation file>
#                            [-C <correction method>] ("none" or "bonferroni") (default "bonferroni")
#                            [-f <custom ontology file>] (default is gene_ontology.obo)
#                            [-b <background population gene list file>]
#                            [-n <num gene products>] (size of background)
#                            [-h] (create html table)
#                            [-H] show help
#                            [-M] generate full pod usage
#                            [-i] (create GO View images)
#                            [-v] (create image-mapped HTML file)
#                            [-p <p-value cutoff>] (default is 0.01)
#                            [-F] (calculate FDR)
#                            [-u <URL prefix>]
#                            [-U <image URL root>]
#                            [-c <max GO child num>]
#                            [-e [!]<evidence code list>]
#                            [-l] (do *not* follow regulation links)
#                            [-B <GraphViz bin dir>]
#                            [-L <GraphViz lib dir>]
#                            [-m <max node>]
#                            [-K <min map with for one line key>]
#                            [-r <height display ratio>]
#                            [-R <width display ratio>]
#                            [-W <minimum map width>]
#                            [-T <min map height for top key>]
#                            [-s <max top node to show>]
#                            [-cache <path>]
#                            [-write-cache]
#                             <file1> <file2> ... <filen>
#
# EXAMPLES:
# ./GOTermFinder.pl -t '/tmp/' -a F -g gene_association.sgd genes.txt
# This uses the gene_association.sgd in the hardcoded $goDir or $goParseDir directories.
# ./GOTermFinder.pl -d '/data/GO/unparsed/' -o '/data/GO/parsed/' -t '/tmp/' -a F -g gene_association.sgd genes.txt
# This uses the gene_association.sgd file within the -d directory (or the cached version in the -o dir if it exists).
# ./GOTermFinder.pl -t '/tmp/' -a F -g /data/tmp/gene_association.sgd genes.txt
# This uses the custom gene_association.sgd file.
# ./GOTermFinder.pl -C none -t '/tmp/' -a F -g /data/tmp/gene_association.sgd -e !IDA,IEA genes.txt
# Use no correction and do not include IDA and IEA annotations.
# ./GOTermFinder.pl -C none -t '/tmp/' -a F -g /data/tmp/gene_association.sgd -e IMP,IDA,IPI genes.txt
# Use no correction and use only IMP, IDA, and IPI annotations.
##############################################################################


use strict;
use warnings;
use diagnostics;

use Fcntl qw/:DEFAULT :flock/;

use CGI qw/:all :html3/;

use Storable;

use Getopt::Long;

use Pod::Usage qw/pod2usage/;

BEGIN { $ENV{'DEVUSER'} = "." if (!$ENV{'DEVUSER'}); }
use lib "/var/www/lib";
#use lib "/Genomics/GO/$ENV{'DEVUSER'}/lib";
#use lib "$ENV{HOME}/GO/lib64/perl5";
#use lib "$ENV{HOME}/GO/GO/lib";

use GO::TermFinder;
use GO::OntologyProvider::OntologyParser;
use GO::OntologyProvider::OboParser;
use GO::TermFinderReport::Text;
use GO::Utils::File    qw (GenesFromFile);
use GO::Utils::General qw (CategorizeGenes);

# local versions of these files
use GO::TermFinderReport::Html;
use GO::AnnotationProvider::AnnotationParser;
use GO::View;
use GO::AnnotationProvider::MetaData; 

my $DEVUSER = (defined($ENV{DEVUSER}) && $ENV{DEVUSER} ne ".");
my $DEBUG = $DEVUSER;


##############################################################################
# Defaults section

my $goDir = "/var/www/data/unparsed";
my $goParseDir = "/var/www/data/parsed";  #!!#
my $pvalueCutOff = 0.01;
my $maxChildGoidNum = 25;
my $noLinkRegulates = 0;
my $confFile = '/var/www/etc/GoView.conf';
my $userConfFile = 'userGoView.conf';
my $maxTopNodeToShow = 6;
my $outDir = "/var/www/tmp/";

#! get from config or command line or something
my $makePS = 1;
my $makeSVG = 1;

# If any of these are changed, they will generate a custom GoView.conf file
my ($binDirDflt, $libDirDflt, $maxNodeDflt, $heightDisplayRatioDflt, $widthDisplayRatioDflt, $minMapWidth4OneLineKeyDflt, $minMapHeight4TopKeyDflt, $minMapWidthDflt);
my $binDir = $binDirDflt = "/usr/bin/"; # '/usr/local/graphviz/bin/';
my $libDir = $libDirDflt = "/usr/lib/"; # '/usr/local/graphviz/lib/graphviz/';
my $maxNode = $maxNodeDflt = 30;
my $heightDisplayRatio = $heightDisplayRatioDflt = 0.8;
my $widthDisplayRatio = $widthDisplayRatioDflt = 0.8;
my $minMapWidth4OneLineKey = $minMapWidth4OneLineKeyDflt = 620;
my $minMapHeight4TopKey = $minMapHeight4TopKeyDflt = 600;
my $minMapWidth = $minMapWidthDflt = 350;

##############################################################################

$|=1;

my $userCacheFile;

my $metaData = GO::AnnotationProvider::MetaData->new();

my ($annotationFile, $aspect, $aspectPreFilter, $backgroundFile, $cacheFilePath, $imageUrlRoot, $inputTotalNumGenes, $writeCache);
# these need long names:
my ($opt_C, $opt_e, $opt_f, $opt_F, $opt_h, $opt_H, $opt_i, $opt_M, $opt_u, $opt_v);

my %opts = (
    'aspect|a=s' => \$aspect,
    'A' => \$aspectPreFilter,
    'background|b=s' => \$backgroundFile,
    'B=s' => \$binDir, # GraphViz bin dir
    'c=i' => \$maxChildGoidNum,
    'C=s' => \$opt_C,  # correction method
    'cache=s' => \$cacheFilePath,
    'd=s' => \$goDir,
    'e=s' => \$opt_e,  # evidence codes
    'f=s' => \$opt_f,  # user ontology file
    'F' => \$opt_F,  # do FDR
    'g=s' => \$annotationFile,
    'h' => \$opt_h,  # generate html
    'H' => \$opt_H,  # print help
    'i' => \$opt_i,  # generate image
    'K=i' => \$minMapWidth4OneLineKey,
    'l' => \$noLinkRegulates,
    'L=s' => \$libDir, # GraphViz lib dir
    'm=i' => \$maxNode,  # max node
    'M' => \$opt_M,  # complete pod usage
    'n=i' => \$inputTotalNumGenes,  # total num genes
    'o=s' => \$goParseDir,
    'p=f' => \$pvalueCutOff,
    'r=f' => \$heightDisplayRatio,
    'R=f' => \$widthDisplayRatio,
    's=i' => \$maxTopNodeToShow,
    't=s' => \$outDir,
    'T=i' => \$minMapHeight4TopKey,
    'u=s' => \$opt_u,  # gene url template
    'U=s' => \$imageUrlRoot,
    'v' => \$opt_v,  # generate image html file
    'W=i' => \$minMapWidth,
    'write-cache' => \$writeCache,
    );

#---check for invalid program switch
Getopt::Long::Configure ("bundling_override", "no_ignore_case");
if (! GetOptions(%opts)) {
   die "Usage: The program switch you entered is invalid\n";
}

my $tryCache = 1;

#---if user uses -H switch, use Pod::Usage to print program usage help message to the screen.
#   if user uses -M switch, use Pod::Usage to print program complete POD to the screen.
#   if user fails to pass the program REQUIRED parameters at the command line to the program, use
#      Pod::Usage to print warning message and synopsis from te program POD to the screen.
&checkUsage; # ($aspect, $annotationFile, $outDir, $opt_H, $opt_M);

my $userAnnotationFile = ($annotationFile =~ /^\//);
&validateGeneAsscFile($annotationFile);
my ($annotationFileBase, $annotationFilePath);
if ($userAnnotationFile) {
    $annotationFile =~ /([^\/]+)\s*$/;
    $annotationFileBase = $1;
    $annotationFilePath = $annotationFile;
    $tryCache = 0;
    print STDERR "no auto cache with user annotation file\n" if ($DEBUG);
} else {
    $annotationFileBase = $annotationFile;
    $annotationFilePath = $goDir."/".$annotationFile;
}
$aspect = uc($aspect);
&validateAspect($aspect);
&validateDirs;  # ($outDir, $goDir, $goParseDir, $binDir, $libDir);
&validateMaxChildGoidNum($maxChildGoidNum);
&validatePvalue($pvalueCutOff);
&validateMaxTopNodeToShow($maxTopNodeToShow);
&isInteger($minMapWidth4OneLineKey, "minMapWidth4OneLineKey (-K)");
&isInteger($maxNode, "maxNode (-m)");
&isFloat($heightDisplayRatio, "heightDisplayRatio (-r)");
&isFloat($widthDisplayRatio, "widthDisplayRatio (-R)");
&isInteger($minMapHeight4TopKey, "minMapHeight4TopKey (-T)");
&isInteger($minMapWidth, "minMapWidth (-W)");
if ($inputTotalNumGenes) {
    &validateTotalNumGenes($inputTotalNumGenes);
    $tryCache = 0;  #! try implementing this with cache
    print STDERR "no auto cache with background override\n" if ($DEBUG);
}

if (($cacheFilePath) && ($cacheFilePath =~ /$goParseDir/)) {
    # we are strict about these paths
    # we will determine the correct file name later
    print STDERR "User-specification of production cache files is not allowed. These files will be selected automatically.\n";
    $cacheFilePath = undef;
    $writeCache = 0;
    $userCacheFile = 0;
} elsif ($cacheFilePath) {
    $userCacheFile = 1;
}
if (!$cacheFilePath) {
    # if $tryCache is true later, this is the path to use
    $cacheFilePath = $goParseDir."/gtfcache_".$aspect."_".$annotationFileBase;
    $writeCache = 0;
    print STDERR "auto cache file path '$cacheFilePath'\n" if ($DEBUG);
}

my $start_time = time;

#---Variables declaration/initialization
my $batchFileName;

my $correction;
if ($opt_C) {
    if ($opt_C eq "none") {
	$correction = "none";
    } elsif (uc($opt_C) ne uc("bonferroni")) {  # default
	print STDERR "Warning: unknown correction method '$opt_C'\n";
    }
}

# program url parameters
my $goidUrl = 'https://www.yeastgenome.org/go/<REPLACE_THIS>';
my $geneUrl;

#---use the user specified ontology aspect at command line to decide from which ontology aspect the ontology file, 
#   parsed_ontology file, and prefound-terms gene-association file should be used
my ($aspectFullName, $ontologyFile, $ontologyFilePath);
if ($aspect eq "F") {
   $aspectFullName = 'function'; 
#   $ontologyFile = 'function.ontology';
} elsif ($aspect eq "C") {
   $aspectFullName = 'component'; 
#   $ontologyFile = 'component.ontology';
} elsif ($aspect eq "P") { 
   $aspectFullName = 'process';
#   $ontologyFile = 'process.ontology'; 
}
$ontologyFile = "gene_ontology.obo";

#user defined ontology file 
if ($opt_f) {
    $ontologyFilePath = $opt_f;
    $tryCache = 0;
    print STDERR "no auto cache with user ontology file\n" if ($DEBUG);
} else {
    $ontologyFilePath = $goDir."/".$ontologyFile;
}
&validateFile($ontologyFilePath);

#---determine whether to use parsed or unparsed ontology file
if (($noLinkRegulates) || ($backgroundFile)) {
    $tryCache = 0;
    print STDERR "no auto cache with -l or background file\n" if ($DEBUG);
}

if ($aspectPreFilter) {
    $tryCache = 0;
    print STDERR "no auto cache supported (yet) with -A\n" if ($DEBUG);
}

# construct evidence code hash -- mark
my %evidenceCodes;
my $evidenceCodesRef = undef;
my $evidenceCodesNotRef = undef;
if ($opt_e) {
    my $neg = 0;
    if (substr($opt_e, 0, 1) eq "-") {
	$opt_e = substr($opt_e, 1);
	$neg = 1;
    }
    my @codes = split(',', $opt_e);
    for (my $c = 0; $c <= $#codes; $c++) {
	$evidenceCodes{uc($codes[$c])} = 1;
    }
    if ($neg) {
	$evidenceCodesNotRef = \%evidenceCodes;
    } else {
	$evidenceCodesRef = \%evidenceCodes;
    }
    print STDERR "no auto cache with -e\n" if ($DEBUG);
    $tryCache = 0;
}

if (($userCacheFile) && ($writeCache)) {
    if (sysopen(LOCK, $cacheFilePath, O_RDWR | O_CREAT)) {
	if (!flock(LOCK, LOCK_EX | LOCK_NB)) {
	    # We are not the first. Wait until whoever has the lock writes the cache. We will not be writing the cache.
	    $writeCache = 0;
	    print "Getting shared lock on $cacheFilePath...\n" if ($DEBUG);
	    flock(LOCK, LOCK_SH);  # blocking
	} else {
	    print "Obtained exclusive lock on $cacheFilePath for writing\n" if ($DEBUG);
	}
    } else {
#	die "Cache file $cacheFilePath does not exist and could not be created\n";
	# it's probably better to let this continue without the cache
	# there could be race conditions when multiple invocations are started at once
	$userCacheFile = 0;
    }
} elsif (($tryCache) || ($userCacheFile)) {
    if (sysopen(LOCK, $cacheFilePath, O_RDONLY)) {
	print "Getting shared lock on $cacheFilePath...\n" if ($DEBUG);
	flock(LOCK, LOCK_SH);  # blocking
	if (!$userCacheFile) {
	    my $mtimeCache = (stat($cacheFilePath))[9];
	    if (((stat($ontologyFilePath))[9] > $mtimeCache) || ((stat($annotationFilePath))[9] > $mtimeCache)) {
		print "Cache $cacheFilePath is out of date\n";
		$tryCache = 0;
		close(LOCK);  # and release shared lock
	    }
	}
    } else {
	# doesn't exist!
	if ($userCacheFile) {
#	    die "Cache file $cacheFilePath does not exist\n";
	    # it's probably better to let this run without the cache
	    # in future we may want to have a flag to force cache use
	    $userCacheFile = 0;
	} else {
	    print "Cache $cacheFilePath cannot be read\n";
	    $tryCache = 0;
	}
    }
}

my $ontology;
my $annotation;
my ($totalNumGenes, $termFinder, $termFinderMessage);

$geneUrl = $metaData->organismGeneUrl($annotationFile, $opt_u);
print "Elapsed time: ", time - $start_time, "\n" if ($DEBUG);

# $writeCache will only be true if a user cache file is opened exclusively for writing and we intend to create the cache
# $tryCache || $userCacheFile will only be true if we have a shared lock on the cache file
if ((($tryCache) || ($userCacheFile)) && (!$writeCache)) {
    
    print "Loading cache $cacheFilePath...\n";

    my $cache = Storable::retrieve($cacheFilePath);
    close(LOCK);

    $annotation = $cache->{annotation};
    $ontology = $cache->{ontology};
    $termFinder = $cache->{termFinder};

    #! compare these values with our calling options
    print "Cache created with:\n";
    foreach (keys(%{$cache})) {
	print "  $_ => ".$cache->{$_}."\n" if ((defined($cache->{$_})) && ($cache->{$_} !~ /HASH/));
    }

    if ($DEBUG) {  #! try testing with totalNumGenes override and cache
    if ($inputTotalNumGenes) {
	# do not allow the user to specify less than what is indicated in the annotation?
	if ($inputTotalNumGenes < $termFinder->totalNumGenes()) {
	    $termFinderMessage = "You have entered fewer genes ($inputTotalNumGenes) for the background than the annotation provider indicates. Thus, assuming the correct total number of genes is that indicated by the annotation provider.\n";
	} else {
	    $termFinder->{'GO::TermFinder::__args'}{totalNumGenes} = $inputTotalNumGenes;
	}
    }
    }

    # we must initialize this or we will segfault
    $termFinder->{'GO::TermFinder::__distributions'} = GO::TermFinder::Native::Distributions->new($termFinder->totalNumGenes);

} else {

    print "Parsing the $ontologyFile file ...\n";

#    print "noLinkRegulates=$noLinkRegulates\n";
#    print "pvalueCutoff=$pvalueCutOff\n";

    if ($ontologyFile =~ /\.obo$/) {
	$ontology = GO::OntologyProvider::OboParser->new(ontologyFile=>$ontologyFilePath, aspect=>$aspect, linkRegulates => !$noLinkRegulates);
    } else {
	$ontology = GO::OntologyProvider::OntologyParser->new(ontologyFile=>$ontologyFilePath);
    }

    # when user specifies the required gene-association file and if its parsed file exists, then use the parsed gene-association file
    # there are no parsed files for selected evidence code combinations (that would be a lot of files!)
    print "Elapsed time: ", time - $start_time, "\n" if ($DEBUG);
    print "Parsing the $annotationFile file ...\n";
    # $annotation = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotationFilePath, evidenceCodes => $evidenceCodesRef, evidenceCodesNot => $evidenceCodesNotRef); # aspect => $aspect);  #! EXPERIMENTAL aspect filter at parse (also need to do this when creating caches)
    $annotation = GO::AnnotationProvider::AnnotationParser->new(annotationFile=>$annotationFilePath, evidenceCodes => $evidenceCodesRef, evidenceCodesNot => $evidenceCodesNotRef, aspect => ($aspectPreFilter)? $aspect : undef);  #! EXPERIMENTAL aspect filter at parse (also need to do this when creating caches)

    # these are the same for all invocations of TermFinder->new:
    my %termFinderOpts = (annotationProvider => $annotation,
			  ontologyProvider => $ontology,
			  aspect => $aspect);

    # if the genome total gene products is known, then use that genome total gene products 
    # as total number of genes for GO::TermFinder
    # if the genome total gene products is not known, then use the number of annotated genes
    # indicated in the genome's gene-association file as population for GO::TermFinder
    if ($backgroundFile) {
	# add this to options for all invocations
#	print "backgroundFile=$backgroundFile\n";
	my @population;
	if (open(POP, $backgroundFile)) {
	    while (<POP>) {
		chomp();
		push(@population, $_);
	    }
	    close(POP);
	} else {
	    die "Cannot open background file $backgroundFile: $!\n";
	}
	$termFinderOpts{population} = \@population;
    } elsif ($inputTotalNumGenes) {
	# do not allow the user to specify less than what is indicated in the annotation?
#	print "input $inputTotalNumGenes anno ", GO::TermFinder->new(%termFinderOpts)->totalNumGenes(),"\n";
	if ($inputTotalNumGenes < GO::TermFinder->new(%termFinderOpts)->totalNumGenes()) {
	    $termFinderMessage = "You have entered fewer genes ($inputTotalNumGenes) for the background than the annotation provider indicates. Thus, assuming the correct total number of genes is that indicated by the annotation provider.\n";
	} else {
	    $termFinderOpts{totalNumGenes} = $inputTotalNumGenes;
	}
    } else {
	$termFinderOpts{totalNumGenes} = $metaData->organismEstimateTotalGeneNum($annotationFile);  # ok if undef
    }

   $termFinder = GO::TermFinder->new(%termFinderOpts);
 
    print "Elapsed time: ", time - $start_time, "\n" if ($DEBUG);

    if ($writeCache) {
	print "Writing cache file $cacheFilePath\n";
	my $cache = { ontology => $ontology, annotation => $annotation, termFinder => $termFinder,
		      aspect => $aspect, evidences => $opt_e, linkRegulates => !$noLinkRegulates,
		      totalNumGenes => $termFinder->totalNumGenes,
		      backgroundFile => $backgroundFile,
		      ontologyFile => $ontologyFilePath, annotationFile => $annotationFilePath };
	Storable::nstore($cache, $cacheFilePath);
	close(LOCK);
    }
}

$totalNumGenes = $termFinder->totalNumGenes();   # may not be scalar(@population) if background provided, may be modified by GO::TermFinder?


if ($opt_e) {
    print "Evidence codes ", ($evidenceCodesRef)? "included":"excluded", ":";
    my $first = 1;
    foreach my $code (keys %evidenceCodes) {
	my ($found, $skipped, $using) = $annotation->evidenceCodeCounts($code);
	print "," if (!$first);
	print " $code (", ($evidenceCodesRef)? $using:$skipped, ")";
	$first = 0;
    }
    print "\n";
#    print "Total used evidence codes: ", $annotation->totalEvidenceCodesUsed, "\n";
}
print "Evidence codes used: ";
my $codesUsed = $annotation->evidenceCodesUsed;
my $first = 1;
foreach my $code (keys %{$codesUsed}) {
    print "," if (!$first);
    print " $code (", $codesUsed->{$code},")";
    $first = 0;
}
print "\n";


$termFinderMessage .= "The total number of genes used to calculate the background distribution of GO terms is $totalNumGenes."; 


#---additional parameters to replace any name=value in GoView.conf file if the user desires  
if (($maxNode != $maxNodeDflt) || ($minMapWidth != $minMapWidthDflt) || ($minMapHeight4TopKey != $minMapHeight4TopKeyDflt) || ($minMapWidth4OneLineKey != $minMapWidth4OneLineKeyDflt) || ($heightDisplayRatio != $heightDisplayRatioDflt) || ($widthDisplayRatio != $widthDisplayRatioDflt) || ($binDir ne $binDirDflt) || ($libDir ne $libDirDflt) || (! -f $confFile)) {
   $confFile = "$outDir/$userConfFile";
   open (CONFFILE, ">$confFile") || die "Cannot create $confFile : $!";
   print CONFFILE "maxNode = $maxNode\n",
                  "minMapWidth = $minMapWidth\n",
                  "minMapHeight4TopKey = $minMapHeight4TopKey\n",
                  "minMapWidth4OneLineKey = $minMapWidth4OneLineKey\n",
                  "widthDisplayRatio = $widthDisplayRatio\n",
                  "heightDisplayRatio = $heightDisplayRatio\n",
                  "binDir = $binDir\n",
                  "libDir = $libDir\n";
   close CONFFILE;
}

#---now create an object of the GO::TermFinderReport::Html module
my $report  = GO::TermFinderReport::Html->new();

#---create a write filehandle for an output file called batchGOViewList.html, for writing
#   links linking to various output data files (e.g text, html, GO::View image files 
#   containing the results of the GO::TermFinder).  User can use this batchGOViewList.html file
#   to view batched output data.
if ($#ARGV > 0) {
    $batchFileName = $$; #assign process ID to batch filename to make batch filename somewhat unique
    open (LIST, ">$outDir/$batchFileName"."_batchGOViewList.html")|| die "Cannot create $outDir/$batchFileName"."_batchGOViewList.html : $!";
}

#---create a html page called batchGOView.html containing two frames.  The left frame holds links to
#   output data, the right frame is used to display the output data corresponding to the link being clicked
#   in the left frame.  User can use this batchGOView.html file to easily browse batched output data without
#   having to leave the web page.  
&GenerateFrameset if ($batchFileName);

#---go through each input file containing the list of genes
foreach my $file (@ARGV){

    my @inputDuplicates;
    my %duplicateHash;

   #check if  input file containing list of genes exist
   &validateFile($file);
   print "Analyzing $file\n";
   #get the genes from the input file
   my @inputGenes = GenesFromFile($file);
   my @genes;

   # bug in GenesFromFile only removes one leading space
   my %geneCheck;    # ignore duplicates
   for (my $g = 0; $g <= $#inputGenes; $g++) {
       my $gene = $inputGenes[$g];
       $gene =~ s/^\s+//;
       if ($geneCheck{$gene}) {
#	   push(@inputDuplicates, $gene);
	   $duplicateHash{$gene} = undef;
	   next;
       }
       $geneCheck{$gene} = 1;
       push(@genes, $gene);
   }

   @inputDuplicates = sort { $a cmp $b } keys %duplicateHash;

   # get the name after the last slash
   $file =~ /([^\/]+)\s*$/;
   my $fileBase = $1;
   $fileBase =~ s/\s+$//;
   # delete anything following the last period
   $fileBase =~ s/\.[^\.]*$//;

   #now we have to decide which input genes we can analyze by categorizing them into those found in gene_association file (@list),
   #   those not found in gene association file (@notFound), and those found but are ambiguous (@ambiguous): 
   my (@list, @notFound, @ambiguous);
   CategorizeGenes(annotation  => $annotation,
                   genes       => \@genes,
                   ambiguous   => \@ambiguous,
                   unambiguous => \@list,
                   notFound    => \@notFound);

   # In one place, when dereferencing IDs to database IDs, if an ID is found to be ambiguous
   # as a synonym but not as a standard name, then it is used as an unambiguous standard name.
   # However, everywhere else in the code, the status as a standard name is not checked when
   # there are issues of ambiguity. The effect we must correct for is that an ID may be used
   # in the query and appear in the output terms, however it can also be listed as ambiguous
   # by CategorizeGenes(). The simplest way to deal with this is to remove from the ambiguous
   # list IDs that are not ambiguous as standard names.
#    for (my $i = 0; $i <= $#ambiguous; $i++ ) {
#	my $id = $ambiguous[$i];
#	if ($annotation->databaseIdByStandardName($id)) {
#	    print "\nRemoving $id from ambiguous list\n";
#	    splice(@ambiguous, $i--, 1);
#	}
#    }

   # GO::TermFinder doesn't seem to report unknown (not found) identifiers except under
   # specific circumstances. So we masquerade here. GOTermFinder CGI depends on the
   # format of this text.
   if (@notFound) {
       print "The following identifiers are not known to the annotation provider:\n";
       print join("\n", @notFound), "\n\n";
   }

   if (@ambiguous) {
       # GOTermFinder CGI relies on a blank line after this list (and none within it)
       # and the wording of this line.
       print "\nThe following identifiers may be ambiguous:\n", join("\n", sort { $a cmp $b } @ambiguous), "\n\n";
   }

   if (@inputDuplicates) {
       print "\nThe following were duplicated in your input list:\n", join("\n", sort { $a cmp $b } @inputDuplicates), "\n\n";
   }

   if (!@list){
      print "No known genes exist in $file, so skipping.\n";
      next;
   }

   #now find the terms for those input genes that are found(@list) and not found (@notFound) in gene_association file 

    print "Elapsed time: ", time - $start_time, "\n" if ($DEBUG);
    print "Find terms from the $aspect ontology for $annotationFile file ...\n";

    my @pvalues;
    if ($opt_F) {
	@pvalues = $termFinder->findTerms(genes => [(@list, @notFound)],
					  calculateFDR => 1, correction => $correction);
    } else {
	@pvalues = $termFinder->findTerms(genes => [(@list, @notFound)], correction => $correction);
    }

   my @discardedGenes = $termFinder->discardedGenes;
   if (@discardedGenes) {
       # GOTermFinder CGI relies on a blank line after this list (and none within it)
       # and the wording of this line.
       print "\nThe following genes were not considered in the pvalue calculations,\nas they were not found in the provided background population:\n", join("\n", sort { $a cmp $b } @discardedGenes), "\n\n";
#   } else {
#       print "No genes discarded\n";
   }

   my ($notFoundCount, $ambiguousCount, $inputCount, $inputDuplicateCount) = ($#notFound+1, $#ambiguous+1, $#list+1, $#inputDuplicates+1);
#   if ($ambiguousCount) {
#       $termFinderMessage = &concat("Of your ", $inputCount, " input genes, ", $notFoundCount, ($notFoundCount > 1)? " were":" was", " unknown and ", $ambiguousCount, ($ambiguousCount > 1)? " were":" was", " ambiguous. ", $termFinderMessage);
#   } else {
#       $termFinderMessage = &concat("Your input list contains ", $notFoundCount + $inputCount," known or unknown but not ambiguous genes. ", $termFinderMessage);
#   }
   my $termFinderMessage_save = $termFinderMessage;  #! ugh
#   $termFinderMessage = &concat("Of your input list, ", $notFoundCount + $inputCount, " genes are known or unknown but not ambiguous. Identifiers unknown to the annotation provider are still included in the statistics.");
#   $termFinderMessage .= &concat(" Also, ", $inputDuplicateCount, ($inputDuplicateCount > 1)? " duplicates were":" duplicate was", " removed from your input list.") if ($inputDuplicateCount);
   $termFinderMessage = join(" ", ("Of your input list,", $notFoundCount + $inputCount, "gene name identifiers are known or unknown but not ambiguous. Identifiers unknown to the annotation provider are still included in the statistics."));
   $termFinderMessage .= join(" ", (" Also,", $inputDuplicateCount, ($inputDuplicateCount > 1)? "duplicates were":"duplicate was", "removed from your input list.")) if ($inputDuplicateCount);
   $termFinderMessage .= " ".$termFinderMessage_save;
   #! it would be best if this were in GO-TermFinder
   my $numDisplayedTerms = 0;
   foreach my $pval (@pvalues) {
#       print STDERR "pval $pval cutoff $pvalueCutOff\n";
       $numDisplayedTerms++ if ($pval->{CORRECTED_PVALUE} <= $pvalueCutOff);
   }
   $termFinderMessage .= " Displaying $numDisplayedTerms terms out of a total of ".scalar(@pvalues)." found.";

   #create a text file containing the significant GO terms found for the list of input genes from the user specified ontology aspect
   my ($textFile, $noTermFoundMessage) = &GenerateTextFile($fileBase, $aspect, $aspectFullName, \@pvalues, $outDir, $pvalueCutOff, $inputCount + $notFoundCount, $totalNumGenes, $termFinderMessage);

   if ($noTermFoundMessage) {

      print $noTermFoundMessage."\n";

  } else {

      print LIST a({-href=>$textFile, -target=>'result'}, $textFile), br if ($batchFileName);

      #now create an object of the GO::View module 
      my $goView = GO::View->new(-ontologyProvider   => $ontology,
				 -annotationProvider => $annotation,
				 -termFinder         => \@pvalues,
				 -aspect             => $aspect,
				 -configFile         => $confFile,
				 -imageDir           => $outDir,
				 -imageName          => $fileBase,
				 -imageUrlRoot       => $imageUrlRoot,
				 -imageLabel         => "Batch GO::View",
				 -nodeUrl            => $goidUrl,
				 -geneUrl            => $geneUrl,
				 -pvalueCutOff       => $pvalueCutOff,
				 -maxTopNodeToShow   => $maxTopNodeToShow,
				 -maxChildGoidNum    => $maxChildGoidNum,
				 -makePS             => $makePS,
				 -makeSVG            => $makeSVG);

      #use the created GO::View object to create a graphical GO::View image file displaying the parent and child relationships 
      #   of the significant GO terms found for the list of input genes from the user specified ontology aspect.
      my ($imageFile, @relativeImageFile, $relativeImageFile);
      if ($opt_i || $opt_v) {
	  if ($goView->graph) {
	      $imageFile = $goView->showGraph;
	      @relativeImageFile = split(/\//, $imageFile); 
	      $relativeImageFile = $relativeImageFile[$#relativeImageFile]; 
	  }
	  &GenerateImageFile($fileBase, $aspect, $aspectFullName, $goView->imageMap, $textFile, $outDir, $termFinderMessage, $noTermFoundMessage);
	  print LIST a({-href=>$relativeImageFile, -target=>'result'}, $relativeImageFile), br if ($batchFileName);
      }

      #create a html table containing the significant GO terms found for the list of input genes from the user specified ontology aspect.
      my ($htmlFile, $relativeHtmlFile);
      if ($opt_h || $opt_v) {
#	  ($htmlFile, $relativeHtmlFile) = &GenerateHTMLFile($fileBase, \@pvalues, $aspect, scalar(@list) + scalar(@notFound), 
	  ($htmlFile, $relativeHtmlFile) = &GenerateHTMLFile($fileBase, \@pvalues, $aspect, $inputCount + $notFoundCount,
							     $totalNumGenes, $outDir, $geneUrl, $goidUrl,  $pvalueCutOff,
							     $textFile, $termFinderMessage, $noTermFoundMessage);
	  print LIST a({-href=>$relativeHtmlFile, -target=>'result'}, $relativeHtmlFile), br if ($batchFileName);
      }

      #create a html file containing both the html table and GO::View image.  The html table contains the significant GO terms found for 
      #   the list of input genes from the user specified ontology aspect.  The GO::View image displays the parent and child relationships
      #   of the significant GO terms.
      my ($imageHtmlFile, $relativeImageHtmlFile);
      if ($opt_v) {
	  ($imageHtmlFile, $relativeImageHtmlFile) = &GenerateImageHTMLFile ($fileBase, $goView->imageMap, $htmlFile,  $textFile, 
									     $outDir, $termFinderMessage, $noTermFoundMessage);
	  print LIST a({-href=>$relativeImageHtmlFile, -target=>'result'}, $relativeImageHtmlFile), br if ($batchFileName);
      }
  }

}# end foreach my $file (@ARGV)

print "Elapsed time ", time - $start_time, ", finishing up\n" if ($DEBUG);

close LIST if ($batchFileName);

print "Done\n";

#if (open(STAT, "/proc/$$/stat")) {
#    print STDERR <STAT>;
#    close(STAT);
#}

exit 0;


##############################################################################
#  SUBROUTINES SECTION
#
##############################################################################

sub checkUsage {
#   my ($opt_a, $opt_g, $opt_t, $opt_H, $opt_M) = @_;

   #---use Pod::Usage to read and parse the POD section of the program
   #   -verbose => 0 (print synopsis)
   #   -verbose => 1 (print synopsis, options, argument)
   #   -verbose => 2 (print the whole pod)
   # print help message to the screen, when user uses -H program switch
   pod2usage(-verbose => 1) && exit 0 if ($opt_H); 
   # print the complet POD to the screen, when user uses -m program switch
   pod2usage(-verbose => 2) && exit 0 if ($opt_M);
   #print the synopsis from the POD to the screen, when user fails to pass the required program argument(s) at the command line to this program
#   pod2usage(-message => "\nWARNING: You forgot to specify the program REQUIRED arguments: (1) the ontology aspect, (2) the gene-association file, (3) the file(s)
#            (containing list of genes) at the command line, OR
#            (4) the directory where the program output files write to.", -verbose => 0) && exit 0 if (! $opt_a || ! $opt_g || ! $opt_t || ! @ARGV);
   pod2usage(-message => "Aspect (-a) is REQUIRED", -verbose => 0) if (!$aspect);
   pod2usage(-message => "Gene association file (-g) is REQUIRED", -verbose => 0) if (!$annotationFile);
#   pod2usage(-message => "Output directory (-t) is REQUIRED", -verbose => 0) if (!$outDir);
   pod2usage(-message => "Query list file is REQUIRED", -verbose => 0) if ((!@ARGV) && (!$writeCache));
}

sub GenerateImageHTMLFile{

   my ($file, $map, $htmlFile, $textFile, $dir, $termFinderMessage, $noTermFoundMessage)  = @_;

   my $imageHtmlFile = $file."_ImageHtml.html";
   my $fullImageHtmlFile = "$dir/$imageHtmlFile";

   open (IMAGEHTML, ">$fullImageHtmlFile") || die "Cannot create $fullImageHtmlFile : $!";

   print IMAGEHTML "<html><body>";

   print IMAGEHTML "<br>";

   #---print message to let viewer know no significant GO terms found for the input list of genes
   if ($noTermFoundMessage) {
      print IMAGEHTML "<b>", "$noTermFoundMessage", "</b>", br, br;
   }  

   #---print message to let viewer know where the total number of genes within a genomes used in GO::TermFinder
   #   comes from, is it from the user specified approximate number of genes within a genome or the from
   #   the total number of annotated genes indicated in the gene-association file
   print IMAGEHTML "<font color=red>", "$termFinderMessage", "</font>";
   print IMAGEHTML "<br>";

   #---print header
   if (!$noTermFoundMessage) {
#      print IMAGEHTML b("Terms from the $aspectFullName ontology exceeding a pvalue cutoff of $pvalueCutOff."), br,br;
#      print IMAGEHTML b("Nodes in the graph are colored according to their p-value. Only terms with significant hits (p-value <= $pvalueCutOff) and their descendents are shown. The limit on the number of descendent trees is $maxChildGoidNum."), br,br;
       print IMAGEHTML b("Nodes in the graph are color-coded according to their p-value. Genes in the GO tree are associated with the GO term(s) to which they are directly annotated. To control the graph size, only significant hits with a p-value <= 0.01 and terms descended from them are included."),br,br;
   }

   #---show the GO::View image on top of the html page.  The GO::View image displays the parent and child relationships
   #   of the significant GO terms found for the list of input genes from the user specified ontology aspect.
   print IMAGEHTML $map if defined $map;
   print IMAGEHTML "</body></html>";

   #---show the html table at the bottom of the html page.  The html table contains the significant GO terms found for 
   #   list of input genes from the user specified ontology aspect.
   open (HTMLFile, "$htmlFile") || die "Cannot create $htmlFile : $!";
   while (<HTMLFile>) {
 
      print(IMAGEHTML $_);
   }

   close IMAGEHTML;
   close HTMLFile;
   return ($fullImageHtmlFile, $imageHtmlFile);
}

sub GenerateTextFile{

   my ($file, $aspect, $aspectFullName, $pvaluesRef, $outDir, $pvalueCutOff, $numGenes, $totalNumGenes,
       $termFinderMessage) = @_;

   my @pvalues = @$pvaluesRef; #dereference

   my $text_report = GO::TermFinderReport::Text->new();

   my $textFile = $file."_terms.txt";
   my $fullTextFile = "$outDir/$textFile";
   my $tabFile = $file."_tab.txt";
   my $fullTabFile = "$outDir/$tabFile";

   open(TAB, ">$fullTabFile") || die "can't create $fullTabFile\n";
   $text_report->print(pvalues => $pvaluesRef,
		       aspect => $aspect,
#		       numGenes => $numGenes,
#		       numGenes => $termFinder->totalNumInputGenes,
		       numGenes => scalar($termFinder->genesDatabaseIds),
		       totalNum => $totalNumGenes,
		       cutoff => $pvalueCutOff,
		       fh => \*TAB,
		       table => 1,
		       correction => $correction);  # need this to set headers correctly
   close(TAB);

#   print "NUMGENES ".scalar($termFinder->genesDatabaseIds),"\n",join("\n", $termFinder->genesDatabaseIds),"\n";

   #---open the text file to write
   open(TEXT, ">$fullTextFile") or die "can't create $fullTextFile\n";

   #---print header for text file
   print TEXT "Terms from the $aspectFullName ontology with p-value <= $pvalueCutOff.\n";
   #---print message to let viewer know where the total number of genes within a genomes used in GO::TermFinder 
   #   comes from, is it from the user specified approximate number of genes within a genome or the from 
   #   the total number of annotated genes indicated in the gene-association file
   print TEXT "\n$termFinderMessage\n\n";

#    if ($#$ambiguousRef >= 0) {
#        print TEXT "Ambiguous identifiers: ", join(", ", @{$ambiguousRef}),"\n\n";
#    }

#    if ($#$notFoundRef >= 0) {
#        print TEXT "Unknown identifiers: ", join(", ", @{$notFoundRef}),"\n\n";
#    }

#    if ($#$discardedRef >= 0) {
#        print TEXT "Discarded identifiers: ",join(", ", @{$discardedRef}),"\n";
#        print TEXT "Discarded identifiers were not found in the background population and were not considered in the pvalue calculations\n\n";
#    }

   #---write to the text file the significant GO terms found for the list of input genes from the user specified ontology aspect
   my $hypothesis = 1;
   my $totalCount = 0;
   my $totalCutoffPvalueCount = 0;

   foreach my $pvalue (@pvalues){
      $totalCount++;
      #next if ($pvalue->{CORRECTED_PVALUE} > $pvalueCutOff);
      if ($pvalue->{CORRECTED_PVALUE} > $pvalueCutOff) {
         $totalCutoffPvalueCount++;
         next
      }
      print TEXT "-- $hypothesis of ", scalar @pvalues, "--\n",
    
      "GOID\t", $pvalue->{NODE}->goid, "\n",
    
      "TERM\t", $pvalue->{NODE}->term, "\n",
    
      "P-VALUE\t", $pvalue->{PVALUE}, "\n",
    
      ((!$correction) || ($correction ne "none"))? "CORRECTED P-VALUE\t".$pvalue->{CORRECTED_PVALUE}."\n" : "",

      "NUM_ANNOTATIONS\t", $pvalue->{NUM_ANNOTATIONS}, " (of ", $pvalue->{TOTAL_NUM_ANNOTATIONS}, ")\n",
    
      "ANNOTATED_GENES\t", join(", ", values (%{$pvalue->{ANNOTATED_GENES}})), "\n\n";
    
      $hypothesis++;
    
   }

   my $noTermFoundMessage;
   if ($totalCutoffPvalueCount == $totalCount) {
     
      $noTermFoundMessage = "\nNo significant GO terms from $aspectFullName ontology with p-value cutoff of ".
                            "$pvalueCutOff were found for your input list of genes.\n";

      print TEXT "$noTermFoundMessage";

   }

   
   close TEXT; 

   return ($textFile, $noTermFoundMessage);
}


sub GenerateImageFile {
   my ($file, $aspect, $aspectFullName, $map, $textFile, $dir, $termFinderMessage, $noTermFoundMessage) = @_;

   my $imageFile = $file."_Image.html";  
   my $fullImageFile = "$dir/$imageFile";

   open (IMAGE, ">$fullImageFile") || die "Cannot create $fullImageFile : $!";
  
   print IMAGE "<html><body>";

   print IMAGE "<br>";

   #---print message to let viewer know no significant GO terms found for the input list of genes
   if ($noTermFoundMessage) {
      print IMAGE "<b>", "$noTermFoundMessage", "</b>", br, br;
      
   }  

   #---print message to let viewer know where the total number of genes within a genomes used in GO::TermFinder
   #   comes from, is it from the user specified approximate number of genes within a genome or the from
   #   the total number of annotated genes indicated in the gene-association file
   print IMAGE "<font color=red>", "$termFinderMessage", "</font>";
   print IMAGE "<br><br>";

   #---print header
   if (!$noTermFoundMessage) {
#      print IMAGE b("Terms from the $aspectFullName ontology with p-value <= $pvalueCutOff."), br,br;
#      print IMAGE b("Nodes in the graph are colored according to their p-value. Only terms with significant hits (p-value <= $pvalueCutOff) and their descendents are shown. The limit on the number of descendent trees is $maxChildGoidNum."), br,br;
       print IMAGE b("Nodes in the graph are color-coded according to their p-value. Genes in the GO tree are associated with the GO term(s) to which they are directly annotated. To control the graph size, only significant hits with a p-value <= 0.01 and terms descended from them are included."),br,br;
   }

   #---show the GO::View image on top of the html page.  The GO::View image displays the parent and child relationships
   #   of the significant GO terms found for the list of input genes from the user specified ontology aspect.
   print IMAGE $map if defined $map;
   print IMAGE "</body></html>";
  
   close IMAGE;
}


sub GenerateHTMLFile{

   my ($file, $pvaluesRef, $aspect, $numGenes, $totalNumGenes, $dir, $geneUrl, $goidUrl,  $pvalueCutOff, $textFile, $termFinderMessage, $noTermFoundMessage) = @_;

   my $htmlFile = $file.".html";
   my $fullHtmlFile = "$dir/$htmlFile";

   open (HTML, ">$fullHtmlFile") || die "Cannot create $fullHtmlFile : $!";

   print HTML "<html><body>";
   
   print HTML br;

   #---print message to let viewer know no significant GO terms found for the input list of genes 
   if ($noTermFoundMessage) {
      print HTML "<b>", "$noTermFoundMessage", "</b>", br, br;   
    
   }

   #---print message to let viewer know where the total number of genes within a genomes used in GO::TermFinder
   #   comes from, is it from the user specified approximate number of genes within a genome or the from
   #   the total number of annotated genes indicated in the gene-association file
   print HTML "<font color=red>".$termFinderMessage."</font>";

   #---create a html table containing the significant GO terms found for the list of input genes from the 
   #   user specified ontology aspect.
   print HTML "<div class=GOResultReport>\n";
   my $numRows = $report->print(pvalues  => $pvaluesRef,
                                aspect   => $aspect,
#                                numGenes => $numGenes,
				numGenes => scalar($termFinder->genesDatabaseIds),
                                totalNum => $totalNumGenes,
                                fh       => \*HTML,
                                #cutoff   => 0.01,
                                pvalueCutOff => $pvalueCutOff,
                                geneUrl  => $geneUrl,
                                goidUrl  => $goidUrl,
				annoFile => $annotationFileBase,
				evidenceCodes => $evidenceCodesRef,
				evidenceCodesNot => $evidenceCodesNotRef,
				correction => $correction);

   print HTML "</div></body></html>";

   close HTML;

   return ($fullHtmlFile, $htmlFile);
}


sub GenerateFrameset{

   #---start an index file that a user can use to browse the output data using frames
   #create a write filehandle for an output file called batchGOView.html   
   open (FRAMES, ">$outDir/$batchFileName"."_batchGOView.html") || die "Cannot create $outDir/$batchFileName"."_batchGOView.html : $!";
   
   # create left and right frames in the batchGOView.html file.  The left frame holds links to output 
   #   data, the right frame is used to display the output data corresponding to the link being clicked 
   #   in the left frame    
   print FRAMES frameset({-cols         => "100, *",
        		   -marginheight => '0',
			   -marginwidth  => '0',
			   -frameborder  => '1',
			   -border       => '1'},
			  
			  frame({'-name'       => "list",
				 -src          => $batchFileName."_batchGOViewList.html",
				 -marginwidth  => 0,
				 -marginheight => 0,
				 -border       => 1}),
		   
			  frame({'-name'       =>'result',
				 -marginwidth  => 0,
				 -marginheight => 0,
				 -border       => 1}));

    close FRAMES;
}


sub validateAspect {
   my($aspect) = @_;
   my $errorMessage;
   #---validate ontology aspect argument
   if ($aspect ne 'F' && $aspect ne 'C' && $aspect ne 'P') {
      $errorMessage = "The ontology aspect $aspect you entered is invalid.  ".
                      "The valid ontology aspect is :F, C or P\n";
      &printErrorMessage($errorMessage);
   }
}

sub validateGeneAsscFile {
   my($annotationFile) = @_;
   my $errorMessage;

   # if it's a custom annotation file it won't be known -- mark
   if ((($userAnnotationFile) && (! -f $annotationFile)) || ((!$userAnnotationFile) && (!$metaData->organismFileExist($annotationFile)))) {
      $errorMessage = "The $annotationFile you entered is not found.\n";
      &printErrorMessage($errorMessage);
    }
}

sub validateFile {
   my($file) = @_;
   my $errorMessage;
   #---check wether the file exists
   if (!(-e $file)) {
      $errorMessage = "The file $file you entered does not exist.\n";
      &printErrorMessage($errorMessage);
   }
}

sub validateTotalNumGenes {
   my ($totalNumGenes) = @_;
   my $errorMessage;
   #---check if the genome total gene products argument is numeric
   if ($totalNumGenes =~ /\D+/) {
      $errorMessage = "The approximate number of gene products within the genome you entered is not numeric.\n";
      &printErrorMessage($errorMessage);
   }
}

sub validateMaxTopNodeToShow {
   my ($maxTopNodeToShow) = @_;
   my $errorMessage;
   #---check if the maxTopNodeToShow argument is numeric
   if ($maxTopNodeToShow =~ /\D+/) {
      $errorMessage = "The maximum number of top significant hits you entered is not numeric.\n";
      &printErrorMessage($errorMessage);
   }   
}

sub validateMaxChildGoidNum {
   my ($maxChildGoidNum) = @_;
   my $errorMessage;
   #---check if the maxTopNodeToShow argument is numeric
   if ($maxChildGoidNum =~ /\D+/) {
      $errorMessage = "The maximum number of descendant trees you entered is not numeric.\n";
      &printErrorMessage($errorMessage);
   }   
}

sub isInteger {
   my ($number, $var) = @_;
   #---check if the number is integer
   if ($number =~ /\D+/) {
      my  $errorMessage = "The GO::View $var you entered is not an integer number.\n";
      &printErrorMessage($errorMessage);
   }
}

sub isFloat {
   my ($number, $var) = @_;
   #---check if the number is float
   if ($number !~ /\d+\.\d+|\d+/) {
      my  $errorMessage = "The GO::View $var you entered is not a float number.\n";
      &printErrorMessage($errorMessage);
   }
}

sub validatePvalue {
   my ($pvalueCutOff) = @_;
   #---check if the GO::TermFinder cut-off p-value is numeric
   if ($pvalueCutOff  !~ /\d+\.\d+|\d+|\d+/) {
      my  $errorMessage = "The GOTermFinder p-value cutoff you entered is not numeric.\n";
      &printErrorMessage($errorMessage);
   }
}

sub printErrorMessage {
   my ($errorMessage) = @_;
   print "$errorMessage";
   exit 1;
}

sub validateDirs {
#   my ($outDir, $goDir, $goParseDir, $binDir, $libDir) = @_;
   #---validate if directory where various GO::TermFinder output files written to exist       
   if ($outDir) {   
      opendir (DIR, $outDir) or die("The directory $outDir you entered does not exist: $!");
   }
   #---validate if directory where ontology and gene-association files store exist
   elsif ($goDir) {
      opendir (DIR, $goDir) or die("The directory $goDir you entered does not exist: $!");
   }
   #---validate if directory where serialized object files of parse ontology files, parsed 
   #   gene-association files, and terms-found gene-association files store exist
   elsif ($goParseDir) {
      opendir (DIR, $goParseDir) or die("The directory $goParseDir you entered does not exist: $!");
   }
   #---validate if directory where the dot and neato locate exists
   elsif ($binDir) {
      opendir (DIR, $binDir) or die("The directory $binDir you entered does not exist: $!");
   }
   #---validate if directory where C libraries for the dot and neato locate exist
   elsif ($libDir) {
      opendir (DIR, $libDir) or die("The directory $libDir you entered does not exist: $!");        
   }
}

##############################################################################
#  PLAIN OLD DOCUMENTATION SECTION
#
##############################################################################
__END__

=pod

=head1 NAME

GOTermFinder.pl - finds shared (significant) GO terms for one file or multiple files, each containing a list of genes 

=head1 SYNOPSIS

GOTermFinder.pl reads through a number of files (each containing a list of genes), finds the shared GO terms (with p-value
cut-off) for each one according to the user specified ontology aspect (P, F, or C) and gene association file, and 
then outputs the following various output files (containing the results of the GO::TermFinder) according to the user's chosen
output file options:

	1. <file name containing list of genes>_terms.txt (text file)

	2. <file name containing list of genes>_tab.txt (tab-delimited text file)

	3. <file name containing list of genes>.html (html table file)

	4. <file name containing list of genes>.png (graphical GO::View image file)

	5. <file name containing list of genes>.svg (graphical GO::View image file)

	6. <file name containing list of genes>.ps (graphical GO::View image file)

	7. <file name containing list of genes>_ImageHtml.html (html file containing both the html table and the GO::View image file)

	8. <file name containing list of genes>_Image.html (html file containing the GO::View image file)

The user is REQUIRED to use program switches -a, -g, -t to specify, respectively, ontology aspect (P, F, or C),
gene association file, and output directory. Also required is the list of files (each containing list of genes) for processing
which must be specified after all other options.

The program allows the user to use following program OPTIONAL switches to overwrite the program default parameters:

        -d: directory to search for ontology and annotation files
	-f: to specify customized ontology file
	-n: to specify the approximate total number of gene products within a genome
	-p: to overwrite the default p-value = 0.01
        -F: to tell the program to calculate the False Discovery Rate (FDR) for each node
        -u: to overwrite the program default gene url for displaying information known about a gene within a genome.  The program
            default gene url(s) known for the genomes as of April 2004 are listed below:
            
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
            Saccharomyces Cerevisiae - https://www.yeastgenome.org/locus/
            Arabidopsis thaliana     - http://arabidopsis.org/servlets/TairObject?accession=gene:
            Caenorhabditis elegans   - http://www.wormbase.org/db/gene/gene?name=
            Danio rerio              - http://zfin.org/cgi-bin/webdriver?MIval=aa-markerview.apg&OID=
            TIGR Geobacter sulfurreducens PCA - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus= 
	    TIGR Pseudomonas syringae DC3000  - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
	    TIGR Trypanosoma brucei chr2      - http://www.tigr.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db=tba1&orf=
	    TIGR Bacillus anthracis	      - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus= 
            TIGR Arabidopsis thaliana	      - http://www.tigr.org/tigr-scripts/euk_manatee/shared/ORF_infopage.cgi?db=ath1&orf=
	    TIGR Coxiella bumetii	      - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
	    TIGR Shewanella oneidensis        - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
	    TIGR Vibrio cholerae	      - http://www.tigr.org/tigr-scripts/CMR2/GenePage.spl?locus=
          
        -e: specify a comma-separated list of evidence codes to select (others are excluded, default is all)
            OR prepend a '!' to specify which evidence codes to exclude
	-h: to produce output file containing html table
	-i: to produce output file containing graphical GO::View image
	-v: to produce output file containing both the html table and image mapped graphical GO::View image
        -U: to specify the root URL for image links

	Following program switches are used to overwrite the default values specified in GO::View configuration file.
	-m: to override the program default GO::View maximum number of displayed nodes = 30
	-W: to override the program default GO::View minimum map width = 350.
	-T: to override the program default GO::View minimum map height of top displayed keys = 600.
	-K: to override the program default GO::View minimum map width of single-row displayed keys = 620.
	-R: to override the program default GO::View ratio of map width over GraphViz defined width =  0.8.
	-r: to override the program default GO::View ratio of map height over the GraphViz defined height = 0.8.
	-B: to override the program default '/sw/bin/' directory where the dot and neato locate.
	-L: to override the program default '/sw/lib/graphviz/' directory where C libraries for the dot and neato locate.
	-N: to override the program default GO::View blank note displayed at the bottom of the map.

The user can get help message of how to use the program by issuing the command: perl B<GOTermFinder.pl> B<-H>, 
and the program's complete POD (plain old documentation) by issuing the command: perl B<GOTermFinder.pl> B<-M>.

Usage example: 

perl B<GOTermFinder.pl> B<-a> F B<-g> gene_association.sgd B<-d> '/usr/local/go/lib/GO/' B<-t> '/tmp/' genes.txt 

The above command (specifying program's all six required options) will find the shared (significant) GO terms (with the program default
GO::TermFinder p-value cut-off of 0.01) from the function ontology aspect for the list of yeast genes contained in the genes.txt file.  

=head1 OPTIONS

All following options, except those marked '(REQUIRED)', are OPTIONAL to the program.  

=over 4

=item B<-a> I<ontology aspect (P, F, or C)> (REQUIRED)

Ontology aspect I<(P, F, or C)>. The user is REQUIRED to use B<-a> switch to specify
the program required ontology aspect.

e.g: perl B<GOTermFinder.pl> B<-a> F -g gene_association.sgd genes.txt

=item B<-g> I<gene-associaton file> (REQUIRED)

Name of gene association file.  The user is REQUIRED to use  B<-g> switch  to
specify the program required gene-association file.

The program will automatically search for a cache file based on this name, the ontology file, and
selected directories.

e.g: perl B<GOTermFinder.pl> -a F B<-g> gene_association.sgd genes.txt

=item B<-t> I<directory> (REQUIRED)

I<directory> where various output files containing the results of the GO:TermFinder are written to.  

e.g: perl B<GOTermFinder.pl> B<-t> '/tmp/' -a F -g gene_association.sgd genes.txt 

=item B<-f> I<ontology file>

Used to specify the ontology file. If this does not start with a '/', then the file is looked for
within the default directory.

=item B<-n> I<number of genes>

Use the B<-n> switch to specify the approximate total number of gene products within a genome.

This is used as the total size of the genome (background) when computing p-values. If it is not specified, then the
size will be taken a) for known genomes, from that specified in AnnotationProvider/MetaData.pm, or b) from the total
number of genes in the annotation.

Caveat: If the specified number is less than the number of genes within the annotation, then the latter is used.

e.g: perl B<GOTermFinder.pl> B<-n> 7266 -a F -g gene_association.sgd genes.txt  

=item B<-d> I<directory>

This flag specifies the default directory to search for ontology and annotation files.

e.g: perl B<GOTermFinder.pl> B<-d> '/usr/local/go/lib/GO/' -a F -g gene_association.sgd genes.txt

=item B<-o> I<directory>

This specifies the I<directory> to search for the pre-parsed cache files.
I<This option is obsolete and not fully supported.>

e.g: perl B<GOTermFinder.pl> B<-o> '/usr/local/go/lib/GOParse/' -a F -g gene_association.sgd genes.txt

=item B<-p> I<pvalue cut off>

The program finds shared (significant) GO terms for the list of genes from the specified ontololgy aspect.
The p-value specifies the minimum significance (terms with lower p-values are reported, those with greater
p-values are not reported). The default p-value cut-off is 0.01.

e.g: perl B<GOTermFinder.pl> B<-p> 0.001 -a F -g gene_association.sgd genes.txt

=item B<-F> 

By default, the program finds significant GO terms with no calculation of False Discovery Rate (FDR) for each node.  Use B<-F> 
to tell the program to calculate the False Discovery Rate (FDR) for each node.

e.g: perl B<GOTermFinder.pl> B<-F> -a F -g gene_association.sgd genes.txt

=item B<-u> I<genome's gene url>

The URL template for linking to external sites from the table. The gene name is simply appended to this.

e.g: perl  B<GOTermFinder.pl> B<-u> 'https://www.yeastgenome.org/locus/' -a F -g gene_association.sgd genes.txt

=item B<-h>

Use B<-h> to have the program produce the results in an html table.

e.g: perl B<GOTermFinder.pl> B<-h> -a F -g gene_association.sgd genes.txt

=item B<-i>

Use B<-i> to have the program use GO::View to produce image files.

e.g: perl B<GOTermFinder.pl> B<-i> -a F -g gene_association.sgd genes.txt

=item B<-v>

Use B<-v> to have the program produce an html file containing hyperlinks and an image map
to go with the image.

e.g: perl B<GOTermFinder.pl> B<-v> -a F -g gene_association.sgd genes.txt

=item B<-m> I<integer number>

The maximum number of GO::View displayed nodes. Use B<-m> switch to override the program default 
value I<30> for the GO::View maxNode specified in the GO::View .conf file.   

e.g: perl B<GOTermFinder.pl> B<-m> 60 -a F -g gene_association.sgd genes.txt

=item B<-W> I<integer number>

The GO::View minimum map width. Use B<-W> switch to override the program default 
value I<350> for the GO::View minamapwidth specified in the GO::View .conf file.   

e.g: perl B<GOTermFinder.pl> B<-W> 700 -a F -g gene_association.sgd genes.txt

=item B<-T> I<integer number>

The minimum map height of the GO::View top displayed keys.  Use B<-T> switch to override the program default
value I<600> for the GO::View minMapHeight4TopKey specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-T> 1200 -a F -g gene_association.sgd genes.txt

=item B<-K> I<integer number> 

The minimum map width of the GO::View single-row displayed keys. Use B<-K> switch to override the program default 
value I<620> for the GO::View minMapWidth4OneLineKey specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-K> 1240 -a F -g gene_association.sgd genes.txt

=item B<-R> I<float number>

The ratio of the GO::View map width over GraphViz defined width. Use B<-R> switch to override the program default
value I<0.8> for the GO::View widthdisplayRatio specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-R> 1.6 -a F -g gene_association.sgd genes.txt

=item B<-r> I<float number>

The ratio of the GO::View map height over the GraphViz defined height. Use B<-r> switch to override the program default
value I<0.8> for the GO::View heightDisplayRatio specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-r> 1.6 -a F -g gene_association.sgd genes.txt

=item B<-B> I<directory path>

The directory where the dot and neato programs are located. Use B<-B> switch to override the program default 
I<'/tools/graphviz/current/bin/'> or that specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-B> 'new/tools/graphviz/current/bin/' -a F -g gene_association.sgd genes.txt

=item B<-L> I<directory path>

The directory where the GraphViz libraries are located.  Use B<-L> switch to overwrite the program default
I<'/tools/graphviz/current/lib/'> or tha specified in the GO::View .conf file.

e.g: perl B<GOTermFinder.pl> B<-L> 'new/tools/graphviz/current/lib/' -a F -g gene_association.sgd genes.txt

=item B<-U> I<image url root>

For the mapped image html file. This is the URL to the actual image.

=item B<-cache> I<cache file>

To reduce runtime, a cache file may be used. This is a Storable-produced file that contains the TermFinder,
Annotation, and Ontology objects. Loading these "frozen" objects is much faster than parsing the text
files and generating background information etc. However, certain parameters affect these objects, and
prevent use of the cache when specified on the command line. Specifically, the cache is not used when:

 a) The annotation file may be customized (assumed when an absolute path is given).
 b) The ontology file may be customized (assumed when -f is used).
 c) The background number (size of genome) is specified with -n.
 d) The -l switch is used (since the cache is generated using regulation links).
 e) A background list is specified with -b.
 f) Any evidence codes are excluded with -e.
 g) The cache is out of date with respect to the ontology or annotation.

=item B<-write-cache> Generate the cache file.

This may be used to create the cache. It will be saved in either the default path or that specified with -cache.

=item B<-H> Print POD usage (this document).

e.g: perl B<GOTermFinder.pl> B<-H>

=item B<-M> Print complete POD usage (this document).

e.g: perl B<GOTermFinder.pl> B<-M>

=item <file1> I<file2> ... I<fileN> (REQUIRED)

The files containing the query identifiers. These must come after all other program switches.

e.g: perl B<GOTermFinder.pl> -a F -g gene_association.sgd B<genes.txt>

=back

=head1 ORIGINAL AUTHOR

Linda McMahan, lmcmahan@genomics.princeton.edu

=head1 EXTENSIVE REVISIONS BY

Mark Schroeder, mark@genomics.princeton.edu

=cut

