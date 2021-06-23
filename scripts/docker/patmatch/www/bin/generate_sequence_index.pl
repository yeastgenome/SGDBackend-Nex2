#!/usr/bin/perl
use strict;

## PatMatch
## Copyright (C) 2004 The Arabidopsis Informatin Resource
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

## Program generates a list of bytes offsets where sequence begins.
## Also generates byte offsets of the start of headers.
##
##
## Output is tab-delimited file of two columns.  First column is the
## byte offset, and the secon dcolumn is the sequence name.  If the
## sequence name begins with '>', then its the start of the FASTA
## header.


my $bytecount = 0;

for my $line (<>) {
    if ($line =~ /^>(\S+)/) {
	print $bytecount , "\t", ">$1", "\n";
	print $bytecount + length($line), "\t", $1, "\n";
    }

    $bytecount += length($line);
}
