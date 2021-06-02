#!/usr/bin/perl
use strict;

## A utility to convert a pattern expression in Patmatch to an expression that
## is understood by nrgrep.  This program does not check the syntax of a
## Patmatch pattern.  It is assumed that it has been done before calling this
## program.
##
## Usage patmatch_to_nrgrep.pl [class] [pattern]
##
## Class options:
## -n: assume nucleotide pattern
## -p: assume protein pattern
## -c: reverse complement nucleotide
##
## Author: Thomas Yan
## Date: 2004/06/01

my $debug = 0;
my $INFINITE = -1;

my $nucleotide = "N";
my $peptide = "P";
my $complement = "C";

my $class = $ARGV[0]; # Nucleotide or peptide 
my $patmatch_pattern = $ARGV[1]; # Patmatch pattern

check_class();
process_pattern();

#############################################################################
##
##  SUBROUTINE NAME
##    check_class()
##
##  SYNOPSIS 
##    check_class()
##
##  DESCRIPTION
##    Ensures that the class from the command line argument is valid.
##    Exits the program if it is not.
##
##  ARGUMENTS
##    none
##
##  RETURN VALUE
##    none
##
#############################################################################
sub check_class
{
    if ($class eq "-n")
    {
	$class = $nucleotide;
    }
    elsif ($class eq "-p")
    {
	$class = $peptide;
    }
    elsif ($class eq "-c")
    {
	$class = $complement;
    }
    else
    {
	print "Invalid class.\n";
	exit(1);
    }
}

#############################################################################
##
##  SUBROUTINE NAME
##    process_pattern()
##
##  SYNOPSIS 
##    process_pattern()
##
##  DESCRIPTION
##    Converts a Patmatch pattern to a nrgrep pattern and prints it to stdout.
##
##  ARGUMENTS
##    none
##
##  RETURN VALUE
##    none
##
#############################################################################
sub process_pattern
{
    my $nrgrep_pattern = prepare_pattern($patmatch_pattern);
    $nrgrep_pattern = fix_wildcards($nrgrep_pattern);
    $nrgrep_pattern = fix_repetitions($nrgrep_pattern);
    $nrgrep_pattern = sub_characters($nrgrep_pattern);
    $nrgrep_pattern = finalize_pattern($nrgrep_pattern);
    print $nrgrep_pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    prepare_pattern()
##
##  SYNOPSIS 
##    prepare_pattern()
##
##  DESCRIPTION
##    Makes all characters upper case and removes spaces.  Get the reverse
##    complement of the pattern if necessary.
##
##  ARGUMENTS
##    $pattern - the pattern to prepare
##
##  RETURN VALUE
##    $pattern after spaces are removed and characters are uppercase
##
#############################################################################
sub prepare_pattern
{
    my $pattern = shift;
    $pattern =~ s/\s//g;
    $pattern = uc($pattern);
    if ($class eq $complement)
    {
	$pattern = get_reverse_complement($pattern);
    }
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    fix_wildcards()
##
##  SYNOPSIS 
##    fix_wildcards()
##
##  DESCRIPTION
##    Substitute Patmatch expression wildcards with nrgrep expression
##    wildcards.
##
##  ARGUMENTS
##    $pattern - the pattern whith Patmatch wildcards
##
##  RETURN VALUE
##    $pattern - the pattern with nrgrep wildcards
##
#############################################################################
sub fix_wildcards
{
    my $pattern = shift;
    if ($class eq $peptide) # peptide case
    {
	$pattern =~ tr/X/\./;
    }
    else # nucleotide case
    {
	$pattern =~ tr/NX/\.\./;
    }
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    fix_repetitions()
##
##  SYNOPSIS 
##    fix_repetitions()
##
##  DESCRIPTION
##    The Patmatch pattern specifies repitions with {m}, {m,}, {,m}, and
##    {m,n}.  These will be replaced by the proper nrgrep representation of
##    repetitions.
##
##  ARGUMENTS
##    $pattern - the pattern whith Patmatch repititions
##
##  RETURN VALUE
##    $pattern - the pattern with nrgrep repititions
##
#############################################################################
sub fix_repetitions
{
    my $pattern = shift;

    # Exit this function if '{' does not exist in the pattern
    if (!($pattern =~ /\{/))
    {
	return $pattern;
    }

    my @nrgrep; # array for storing nrgrep pattern characters
    my @patmatch = split(//, $pattern); # array containing Patmatch pattern
    
    foreach my $char (@patmatch)
    {
	if ($char eq '}')
	{
	    @nrgrep = process_repitition(@nrgrep);
	}
	else
	{
	    push(@nrgrep, $char);
	}
    }

    my $nrgrep_pattern = join("", @nrgrep);
    return $nrgrep_pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    process_repitition()
##
##  SYNOPSIS 
##    process_repitition()
##
##  DESCRIPTION
##    A Patmatch repitition has been encountered so modify the repitition to
##    a nrgrep repitition.
##
##  ARGUMENTS
##    @nrgrep an array of characters containing the Patmatch repitition
##
##  RETURN VALUE
##    @nrgrep an array of strings containing the nrgrep repitition
##
#############################################################################
sub process_repitition
{
    my @nrgrep = @_;

    my $rep_info = extract_repitition_information(\@nrgrep);
    my $repeat_pattern = extract_repeat_pattern(\@nrgrep);
    append_nrgrep_repeats(\@nrgrep, $rep_info, $repeat_pattern);

    return @nrgrep;
}

#############################################################################
##
##  SUBROUTINE NAME
##    extract_repitition_information()
##
##  SYNOPSIS 
##    extract_repitition_information()
##
##  DESCRIPTION
##    Extracts and removes repitition information from a pattern array.
##
##  ARGUMENTS
##    $nrgrep_ref an array reference to an array containing repitition info
##
##  RETURN VALUE
##    $rep_info the repitition information extracted from the array
##
#############################################################################
sub extract_repitition_information
{
    my $nrgrep_ref = shift;
    
    my @rep_info_array;
    my $continue = 1;
    while($continue)
    {
	my $pat_char = pop(@$nrgrep_ref);
	if ($pat_char eq '{')
	{
	    $continue = 0;
	}
	else
	{
	    unshift(@rep_info_array, $pat_char);
	}
    }
    my $rep_info = join("", @rep_info_array);
    return $rep_info;
}

#############################################################################
##
##  SUBROUTINE NAME
##    extract_repeat_pattern()
##
##  SYNOPSIS 
##    extract_repeat_pattern()
##
##  DESCRIPTION
##    Extracts and removes repeat pattern from a pattern array.
##    Example 1: argument = ATG
##               return value = G
##    Example 2: argument = AT(TATA)
##               return value = (TATA)
##    Example 3: argument = AT[TAG]
##               return value = [TAG]
##
##  ARGUMENTS
##    $nrgrep_ref an array reference to an array containing repeat_pattern
##
##  RETURN VALUE
##    $rep_pat the repeat pattern extracted from the array
##
#############################################################################
sub extract_repeat_pattern()
{
    my $nrgrep_ref = shift;
    
    my $char = pop(@$nrgrep_ref);
    if (($char eq ')') || ($char eq ']'))
    {
	my @bracket_stack; # stack of brackets
	my $right_bracket = $char;
	my $left_bracket;
	if ($char eq ')')
	{
	    $left_bracket = '(';
	}
	else
	{
	    $left_bracket = '[';
	}
	push(@bracket_stack, $right_bracket);

	my @repeat; # array containing the repeat characters
	unshift(@repeat, $char);
	
	my $stack_length = @bracket_stack;
	while ($stack_length > 0)
	{
	    $char = pop(@$nrgrep_ref);
	    unshift(@repeat, $char);
	    if ($char eq $right_bracket)
	    {
		push(@bracket_stack, $char);
	    }
	    elsif ($char eq $left_bracket)
	    {
		pop(@bracket_stack);
	    }
	    $stack_length = @bracket_stack;
	}
	
	my $rep_pat = join("", @repeat);
	return $rep_pat;
    }
    else
    {
	return $char;
    }
}

#############################################################################
##
##  SUBROUTINE NAME
##    append_nrgrep_repeats()
##
##  SYNOPSIS 
##    append_nrgrep_repeats()
##
##  DESCRIPTION
##    Appends a repeat pattern to an array reference according to repitition
##    information.
##
##  ARGUMENTS
##    $nrgrep_ref an array reference to a pattern array
##    $repeat_info information on how many times to repeat the repeat pattern
##    $repeat_pattern the pattern to repeat
##
##  RETURN VALUE
##    none
##
#############################################################################
sub append_nrgrep_repeats
{
    my $nrgrep_ref = shift;
    my $repeat_info = shift;
    my $repeat_pattern = shift;

    my ($lower, $upper) = process_repeat_info($repeat_info);
    my $repeats = build_nrgrep_repeat($lower, $upper, $repeat_pattern);
    push(@$nrgrep_ref, $repeats);
}

#############################################################################
##
##  SUBROUTINE NAME
##    process_repeat_info()
##
##  SYNOPSIS 
##    process_repeat_info()
##
##  DESCRIPTION
##    Processes repeat information to determine lower and upper bounds.
##
##  ARGUMENTS
##    $repeat_info repeat information extracted from a Patmatch pattern
##                 formats: m
##                          ,m
##                          m,
##                          m,n
##
##  RETURN VALUE
##    $lower lower bound
##    $upper upper bound
##
#############################################################################
sub process_repeat_info
{
    my $repeat_info = shift;

    my $lower = 0;
    my $upper = 0;
    my @bounds = split(",", $repeat_info);
    if ($repeat_info =~ /^,\d+/)
    {
	$upper = $bounds[1];
    }
    elsif ($repeat_info =~ /\d+,$/)
    {
	$lower = $bounds[0];
	$upper = $INFINITE;
    }
    elsif ($repeat_info =~ /^\d+$/)
    {
	$lower = $repeat_info;
	$upper = $repeat_info;
    }
    elsif ($repeat_info =~ /^\d+,\d+$/)
    {
	$lower = $bounds[0];
	$upper = $bounds[1];
    }

    return $lower, $upper;
}

#############################################################################
##
##  SUBROUTINE NAME
##    build_nrgrep_repeat()
##
##  SYNOPSIS 
##    build_nrgrep_repeat()
##
##  DESCRIPTION
##    Creates an nrgrep repeat pattern when given a pattern to repeat and
##    the number of times to repeat the pattern
##
##  ARGUMENTS
##    $lower the lower bound on the number of times to repeat the pattern
##    $upper the upper bound on the number of times to repeat the pattern
##           if this value is $INFINITE then the upper bound is infinite
##    $pattern the nucleotide pattern to repeat
##
##  RETURN VALUE
##    $nrgrep_repeat the nrgrep repeat pattern
##
#############################################################################
sub build_nrgrep_repeat
{
    my $lower = shift;
    my $upper = shift;
    my $pattern = shift;

    my @repeat_array;
    
    # Add the pattern $lower times to the repeat array
    for (my $i = 0; $i < $lower; $i++)
    {
	push(@repeat_array, $pattern);
    }

    # Add the pattern $upper - $lower times followed by a '?' or
    # if $upper == $INFINITE then add the pattern once followed by a '*'
    if ($upper == $INFINITE)
    {
	my $infinite_pattern = $pattern . "*";
	push(@repeat_array, $infinite_pattern);
    }
    else
    {
	my $num = $upper - $lower;
	my $possible_pattern = $pattern . "?";
	for (my $i = 0; $i < $num; $i++)
	{
	    push(@repeat_array, $possible_pattern);
	}
    }

    my $nrgrep_repeat = join("", @repeat_array);
    return $nrgrep_repeat;
}

#############################################################################
##
##  SUBROUTINE NAME
##    sub_characters()
##
##  SYNOPSIS 
##    sub_characters()
##
##  DESCRIPTION
##    Substitutes IUPAC wildcard characters with subsets
##
##  ARGUMENTS
##    $pattern a pattern with IUPAC characters
##
##  RETURN VALUE
##    $pattern the given pattern with IUPAC characters replaced by subsets
##
#############################################################################
sub sub_characters
{
    my $pattern = shift;
    
    if ($class eq $peptide) # peptide pattern
    {
	$pattern =~ s/J/\[IFVLWMAGCY\]/g;
	$pattern =~ s/O/\[TSHEDQNKR\]/g;
	$pattern =~ s/B/\[DN\]/g;
	$pattern =~ s/Z/\[EQ\]/g;
    }
    else # nucleotide pattern
    {
	$pattern =~ s/R/\[AG\]/g;
	$pattern =~ s/Y/\[CT\]/g;
	$pattern =~ s/S/\[GC\]/g;
	$pattern =~ s/W/\[AT\]/g;
	$pattern =~ s/M/\[AC\]/g;
	$pattern =~ s/K/\[GT\]/g;
	$pattern =~ s/V/\[ACG\]/g;
	$pattern =~ s/H/\[ACT\]/g;
	$pattern =~ s/D/\[AGT\]/g;
	$pattern =~ s/B/\[CGT\]/g;
    }
    
    $pattern = remove_nested_brackets($pattern);
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    remove_nested_brackets()
##
##  SYNOPSIS 
##    remove_nested_brackets()
##
##  DESCRIPTION
##    Removes nested brackets in a pattern.  Also ensures a character does
##    not appear more than once between brackets.  Nested brackets can be
##    caused by the substitution of wildcard characters with subsets.
##    Example 1: argument = TA[A[CT]]
##               return value = TA[A[CT]]
##    Example 2: argument = TA[A[AG]]
##               return value = TA[AG]
##    Example 3: argument = TA[ATAG]
##               return value = TA[ATG]
##
##  ARGUMENTS
##    $pattern a pattern
##
##  RETURN VALUE
##    $pattern the pattern with nested brackets removed
##
#############################################################################
sub remove_nested_brackets
{
    my $pattern = shift;

    my @before_pattern = split(//, $pattern);
    my @after_pattern;
    my @bracket_stack; # left bracket stack
    my %char_hash; # hash containing characters between brackets

    foreach my $char (@before_pattern)
    {
	if ($char eq '[')
	{
	    my $stack_length = @bracket_stack;
	    if ($stack_length == 0)
	    {
		push(@after_pattern, $char);
	    }
	    push(@bracket_stack, $char);
	}
	elsif ($char eq ']')
	{
	    pop(@bracket_stack);
	    my $stack_length = @bracket_stack;
	    if ($stack_length == 0)
	    {
		push(@after_pattern, $char);
	        %char_hash = (); # Remove all elements from %char_hash
	    }
	}
	else
	{
	    my $stack_length = @bracket_stack;
	    if ($stack_length == 0)
	    {
		push(@after_pattern, $char);
	    }
	    else
	    {
		if (exists($char_hash{$char}))
		{
		    # do nothing, $char aleady exists within [...
		}
		else
		{
		    push(@after_pattern, $char);
		    $char_hash{$char} = 1;
		}
	    }
	}
    }

    $pattern = join("", @after_pattern);

    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    finalize_pattern()
##
##  SYNOPSIS 
##    finalize_pattern()
##
##  DESCRIPTION
##    Place the entire pattern in parentheses except for anchors.
##    Anchors are converted to nrgrep anchors.
##
##  ARGUMENTS
##    $pattern a pattern
##
##  RETURN VALUE
##    $pattern the finalized nrgrep pattern
##
#############################################################################
sub finalize_pattern
{
    my $pattern = shift;

    if (($pattern =~ /^</) && ($pattern =~ />$/))
    {
	$pattern =~ s/<//;
	$pattern =~ s/>//;
	$pattern = '^(' . $pattern . ')$';
    }
    elsif ($pattern =~ /^</)
    {
	$pattern =~ s/<//;
	$pattern = '^(' . $pattern . ')';
    }
    elsif ($pattern =~ />$/)
    {
	$pattern =~ s/>//;
	$pattern = '(' . $pattern . ')$';
    }
    else
    {
	$pattern = '(' . $pattern . ')';
    }
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    get_reverse_complement()
##
##  SYNOPSIS 
##    get_reverse_complement()
##
##  DESCRIPTION
##    Get the reverse complement of a pattern.
##
##  ARGUMENTS
##    $pattern - the pattern to get reverse complement of
##
##  RETURN VALUE
##    $pattern - the reverse complement of the given pattern
##
#############################################################################
sub get_reverse_complement
{
    my $pattern = shift;

    $pattern = complement_nucleotides($pattern);
    $pattern = reverse_pattern($pattern);
    debug($pattern);
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    complement_nucleotides()
##
##  SYNOPSIS 
##    complement_nucleotides()
##
##  DESCRIPTION
##    Complement a given pattern.
##
##  ARGUMENTS
##    $pattern - the upper case pattern to get the complement of
##
##  RETURN VALUE
##    $pattern - the complement of the given pattern
##
#############################################################################
sub complement_nucleotides
{
    my $pattern = shift;

    $pattern =~ tr/ATCGRYSWMKVHDB/TAGCYRSWKMBDHV/;
    if ($pattern =~ /^</)
    {
	$pattern =~ s/^</>/;
    }
    if ($pattern =~ />$/)
    {
	$pattern =~ s/>$/</;
    }
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    reverse_pattern()
##
##  SYNOPSIS 
##    reverse_pattern()
##
##  DESCRIPTION
##    Reverse a given pattern.
##
##  ARGUMENTS
##    $pattern - the upper case pattern to reverse
##
##  RETURN VALUE
##    $pattern - reverse of the given pattern
##
#############################################################################
sub reverse_pattern
{
    my $pattern = shift;
    
    my @pat_array = split(//, $pattern);
    my @reverse;
    my $pat_length = @pat_array;
    while ($pat_length > 0)
    {
	my $char = pop(@pat_array);
	if ($char =~ m/[\)\]\}]/) # Found a grouping
	{
	    my $group = extract_group($char, \@pat_array);
	    push(@reverse, $group);
	}
	else
	{
	    push(@reverse, $char);
	}
	$pat_length = @pat_array;
    }
    $pattern = join("", @reverse);
    return $pattern;
}

#############################################################################
##
##  SUBROUTINE NAME
##    extract_group()
##
##  SYNOPSIS 
##    extract_group()
##
##  DESCRIPTION
##    Function to extract a reverse group between (), [], or <something>{}
##    Example 1: arguments = } and GG(CTA){2,3
##               return value = (ATC){2,3}
##    Example 2: arguments = } and GGCTA{2,3
##               return value = A{2,3}
##    Example 3: arguments = ) and GGCT(AC
##               return value = (CA)
##    Example 4: arguments = ) and GGCT(ATA[CT]A
##               return value = (A[TC]ATA)
##
##  ARGUMENTS
##    $closer ')', ']', or '}' ... the charcter that closes the group
##    $pat_ref a reference to an array containing the pattern to extract
##             a group from
##
##  RETURN VALUE
##    $group a reverse complement of a grouping
##
#############################################################################
sub extract_group
{
    my $closer = shift;
    my $pat_ref = shift;

    my $opener = get_open_group_char($closer);

    my @group_arr;
    unshift(@group_arr, $closer);
    
    my $not_done = 1;
    my @internal_group_chars;
    while ($not_done)
    {
	my $char = pop(@$pat_ref);
	if ($char eq $opener)
	{
	    if (!($opener eq '{'))
	    {
		my $group_chars = join("", @internal_group_chars);
		unshift(@group_arr, $group_chars);
		unshift(@group_arr, $char);
		$not_done = 0;
	    }
	    else
	    {
		unshift(@group_arr, $char);
		my $repeater = pop(@$pat_ref);
		if ($repeater =~ m/[\]\)]/)
		{
		    my $group = extract_group($repeater, $pat_ref);
		    unshift(@group_arr, $group);
		}
		else
		{
		    unshift(@group_arr, $repeater);
		}
		$not_done = 0;
	    }
	}
	elsif ($char =~ m/[\)\]\}]/)
	{
	    my $group = extract_group($char, $pat_ref);
	    push(@internal_group_chars, $group);
	}
	else
	{
	    if ($closer eq '}')
	    {
		unshift(@group_arr, $char);
	    }
	    else
	    {
		push(@internal_group_chars, $char);
	    }
	}
    }

    my $group = join("", @group_arr);
    return $group;
}

#############################################################################
##
##  SUBROUTINE NAME
##    get_open_group_char()
##
##  SYNOPSIS 
##    get_open_group_char()
##
##  DESCRIPTION
##    Function to get an group "opener" character based on a group closing
##    character.
##
##  ARGUMENTS
##    $closer ')', ']', or '}'
##
##  RETURN VALUE
##    $opener the corresponding '(', '[', or '{'
##
#############################################################################
sub get_open_group_char
{
    my $closer = shift;
    
    my $opener;
    if ($closer eq ')')
    {
	$opener = '(';
    }
    elsif ($closer eq ']')
    {
	$opener = '[';
    }
    elsif ($closer eq '}')
    {
	$opener = '{';
    }
    else
    {
	debug("Encountered a bad grouping character at get_open_group_char()");
    } 
    
    return $opener;
}

# Debug function
sub debug
{
    my $msg = shift;
    if ($debug)
    {
	print STDERR $msg, "\n";
    }
}
