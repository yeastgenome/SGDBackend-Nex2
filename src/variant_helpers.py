from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
import json
from src.models import DBSession, Locusdbentity, Dnasequencealignment, \
     Proteinsequencealignment, Sequencevariant, Taxonomy, Goannotation,\
     Proteindomainannotation, Dnasequenceannotation, Proteinsequenceannotation,\
     Contig
from src.curation_helpers import get_curator_session
from scripts.loading.util import strain_order

TAXON = 'TAX:559292'

def get_variant_data(request):

    sgdid = request.matchdict['id'].upper()

    dbentity = DBSession.query(Locusdbentity).filter_by(sgdid=sgdid).one_or_none()

    if dbentity is None:
        return {}

    taxonomy = DBSession.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    
    data = { 'sgdid': dbentity.sgdid,
             'name': dbentity.display_name,
             'format_name': dbentity.systematic_name,
             'category': dbentity.subclass.lower(),
             'url': dbentity.obj_url + '/overview',
             'href': dbentity.obj_url + '/overview',
             'description': dbentity.headline
    }

    locus_id = dbentity.dbentity_id

    dnaseqannot = DBSession.query(Dnasequenceannotation).filter_by(dbentity_id=locus_id, dna_type='GENOMIC', taxonomy_id=taxonomy_id).one_or_none()

    data['strand'] = dnaseqannot.strand
    data['chrom_start'] = dnaseqannot.start_index
    data['chrom_end'] = dnaseqannot.end_index
    data['dna_length'] = len(dnaseqannot.residues)
    
    contig = DBSession.query(Contig).filter_by(contig_id=dnaseqannot.contig_id).one_or_none()

    data['contig_name'] = contig.display_name
    data['contig_href'] = contig.obj_url + '/overview'

    protseqannot = DBSession.query(Proteinsequenceannotation).filter_by(dbentity_id=locus_id, taxonomy_id=taxonomy_id).one_or_none()

    data['protein_length'] = len(protseqannot.residues)

    go_terms = []
    for x in DBSession.query(Goannotation).filter_by(dbentity_id=locus_id).all():
        if x.go.display_name not in go_terms:
            go_terms.append(x.go.display_name)
    go_terms.sort()
    data['go_terms'] = go_terms

    data['protein_domains'] = []
    for x in DBSession.query(Proteindomainannotation).filter_by(dbentity_id=locus_id).all():
        row = { "id": x.proteindomain.proteindomain_id,
                "start": x.start_index,
                "end": x.end_index,
                "sourceName": x.proteindomain.source.display_name,
                "sourceId": x.proteindomain.source_id,
                "name": x.proteindomain.display_name,
                "href": x.proteindomain.obj_url + '/overview'
        }
        data['protein_domains'].append(row)
    
    # absolute_genetic_start = 3522089??   
    # 'dna_scores': locus['dna_scores'],
    # 'protein_scores': locus['protein_scores'],
    
    strain_to_id = strain_order()
    dna_seqs = []
    snp_seqs = []
    strain_to_snp = {}
    strain_to_dna = {}
    block_sizes = []
    block_starts = []
    for x in DBSession.query(Dnasequencealignment).filter_by(dna_type='genomic', locus_id=locus_id).all():
        [name, strain] = x.display_name.split('_')
        if strain == 'S288C':
            block_sizes = x.block_sizes.split(',')
            block_starts = x.block_starts.split(',')
        strain_to_dna[strain] = { "strain_display_name": strain,
                                  "strain_link": "/strain/" + strain.replace(".", "") + "/overview",
                                  "strain_id": strain_to_id[strain],
                                  "sequence": x.aligned_sequence
        }
        i = strain_to_id[strain] - 1
        strain_to_snp[strain] = { "snp_sequence": x.snp_sequence,
                                  "name": strain,
                                  "id":  strain_to_id[strain] }
        
    for i in range(0, len(block_sizes)): 
        block_sizes[i] = int(block_sizes[i])
    for i in range(0, len(block_starts)):
        block_starts[i] = int(block_starts[i])
    data['block_sizes'] = block_sizes
    data['block_starts'] = block_starts
    for strain in sorted(strain_to_id, key=strain_to_id.get):
        if strain in strain_to_snp:
            snp_seqs.append(strain_to_snp[strain])
        if strain in strain_to_dna:
            dna_seqs.append(strain_to_dna[strain])
            
    data['aligned_dna_sequences'] = dna_seqs
    data['snp_seqs'] = snp_seqs
    
    protein_seqs = []
    strain_to_protein = {}
    for x in DBSession.query(Proteinsequencealignment).filter_by(locus_id=locus_id).all():
        [name, strain] = x.display_name.split('_')
        strain_to_protein[strain] = { "strain_display_name": strain,
                                      "strain_link": "/strain/"	+ strain.replace(".", "") + "/overview",
                                      "strain_id": strain_to_id[strain],
                                      "sequence": x.aligned_sequence
        }
    for strain in sorted(strain_to_id, key=strain_to_id.get):
        if strain in strain_to_protein:
            protein_seqs.append(strain_to_protein[strain])
    data['aligned_protein_sequences'] = protein_seqs

    variant_dna = []
    variant_protein = []
    dna_snp_positions = []
    dna_deletion_positions = []
    dna_insertion_positions = []
    insertion_index = 0
    deletion_index = 0
    snp_index = 0
    for x in DBSession.query(Sequencevariant).filter_by(locus_id=locus_id).order_by(Sequencevariant.seq_type, Sequencevariant.variant_type, Sequencevariant.snp_type, Sequencevariant.start_index, Sequencevariant.end_index).all():
        if x.seq_type == 'DNA':
            dna_row = { "start": x.start_index,
                        "end": x.end_index,
                        "score": x.score,
                        "variant_type": x.variant_type }
            if x.snp_type:
                dna_row['snp_type'] = x.snp_type.capitalize()
            variant_dna.append(dna_row)

            ### 
            if x.variant_type == 'Insertion':
                dna_insertion_positions.append((x.start_index, x.end_index))
            elif x.variant_type == 'Deletion':
                dna_deletion_positions.append((x.start_index, x.end_index))
            elif x.variant_type == 'SNP' and x.snp_type == 'nonsynonymous':
                dna_snp_positions.append((x.start_index, x.end_index))
                
        if x.seq_type == 'protein':
            
            dna_start = 0
            dna_end = 0
            if x.variant_type == 'Insertion':
                if len(dna_insertion_positions) > insertion_index:
                    (dna_sart, dna_end) = dna_insertion_positions[insertion_index]
                    insertion_index = insertion_index + 1
                else: # it should never go to this step
                    if x.start_index == 1:
                        dna_start = 1
                        dna_end = x.end_index*3
                    else:
                        (dna_start, dna_end) = (x.start_index*3, x.end_index*3)
            elif x.variant_type == 'Deletion':
                if len(dna_deletion_positions) > deletion_index:
                    (dna_start, dna_end) = dna_deletion_positions[deletion_index]
                    deletion_index = deletion_index + 1
                else: # it should never go to this step   
                    if x.start_index == 1:
                        dna_start = 1
                        dna_end = x.end_index*3
                    else:
                        (dna_start, dna_end) = (x.start_index*3, x.end_index*3)
            elif x.variant_type == 'SNP':
                if len(dna_snp_positions) > snp_index:
                    (dna_start, dna_end) = dna_snp_positions[snp_index]
                    snp_index = snp_index + 1
                else: # it should never go to this step
                    if x.start_index == 1:
                        dna_start = 1
                        dna_end = x.end_index*3
                    else:
                        (dna_start, dna_end) = (x.start_index*3, x.end_index*3)
                
            protein_row = { "start": x.start_index,
                            "end": x.end_index,
                            "score": x.score,
                            "variant_type": x.variant_type,
                            "dna_start": dna_start,
                            "dna_end": dna_end }
            if x.variant_type not in ['Insertion', 'Deletion']:
                protein_row['snp_type'] = ""

            variant_protein.append(protein_row)
            
    data['variant_data_dna'] = variant_dna
    data['variant_data_protein'] = variant_protein
    
    return data
 
    
