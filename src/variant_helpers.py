from collections import OrderedDict
from sqlalchemy import or_
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
import json
from src.models import DBSession, Dbentity, Locusdbentity, Dnasequencealignment, \
     Proteinsequencealignment, Sequencevariant, Taxonomy, Goannotation,\
     Proteindomainannotation, Dnasequenceannotation, Proteinsequenceannotation,\
     Contig, So, Go, Goannotation
from src.curation_helpers import get_curator_session
from scripts.loading.util import strain_order

TAXON = 'TAX:559292'

def get_dna_alignment_data(locus_id, dna_type, strain_to_id):

    dna_seqs = []
    snp_seqs = []
    strain_to_snp = {}
    strain_to_dna = {}
    block_sizes = []
    block_starts = []
    name = None
    start = None
    end = None
    for x in DBSession.query(Dnasequencealignment).filter_by(dna_type=dna_type, locus_id=locus_id).all():
        if x.display_name.endswith('S288C'):
            start = x.contig_start_index
            end = x.contig_end_index
        strain = None
        if dna_type == 'genomic':
            [name, strain] = x.display_name.split('_')
        else:
            [name1, name2, strain] = x.display_name.split('_')
            name = name1 + "_" + name2
        if strain == 'S288C':
            block_sizes = x.block_sizes.split(',')
            if dna_type == 'genomic':
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
    if dna_type != 'genomic':
        block_starts = [0]
    
    for strain in sorted(strain_to_id, key=strain_to_id.get):
        if strain in strain_to_snp:
            snp_seqs.append(strain_to_snp[strain])
        if strain in strain_to_dna:
            dna_seqs.append(strain_to_dna[strain])

    return (name, start, end, dna_seqs, snp_seqs, block_starts, block_sizes)
        
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
        
    strain_to_id = strain_order()

    (name, start, end, dna_seqs, snp_seqs, block_starts, block_sizes) = get_dna_alignment_data(locus_id, 'genomic', strain_to_id)
    data['block_sizes'] = block_sizes
    data['block_starts'] = block_starts
    data['aligned_dna_sequences'] = dna_seqs
    data['snp_seqs'] = snp_seqs

    (name, start, end, dna_seqs, snp_seqs, block_starts, block_sizes) = get_dna_alignment_data(locus_id, 'downstream IGR', strain_to_id)
    if end and start:
        data['downstream_format_name'] = name
        data['downstream_chrom_start'] = start
        data['downstream_chrom_end'] = end
        data['downstream_dna_length'] = end - start + 1
        data['downstream_block_sizes'] = block_sizes
        data['downstream_block_starts'] = block_starts
        data['downstream_aligned_dna_sequences'] = dna_seqs
        data['downstream_snp_seqs'] = snp_seqs
    
    (name, start, end, dna_seqs, snp_seqs, block_starts, block_sizes) = get_dna_alignment_data(locus_id, 'upstream IGR', strain_to_id)
    if end and start:
        data['upstream_format_name'] = name
        data['upstream_chrom_start'] = start
        data['upstream_chrom_end'] = end
        data['upstream_dna_length'] = end - start + 1
        data['upstream_block_sizes'] = block_sizes
        data['upstream_block_starts'] = block_starts
        data['upstream_aligned_dna_sequences'] = dna_seqs
        data['upstream_snp_seqs'] = snp_seqs
    ################################# 
    
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
    downstream_variant_dna = []
    upstream_variant_dna = []
    dna_snp_positions = []
    dna_deletion_positions = []
    dna_insertion_positions = []
    insertion_index = 0
    deletion_index = 0
    snp_index = 0
    for x in DBSession.query(Sequencevariant).filter_by(locus_id=locus_id).order_by(Sequencevariant.seq_type, Sequencevariant.variant_type, Sequencevariant.snp_type, Sequencevariant.start_index, Sequencevariant.end_index).all():

        if x.seq_type == 'downstream IGR':
            dna_row = { "start": x.start_index,
                        "end": x.end_index,
                        "score": x.score,
                        "variant_type": x.variant_type }
            if x.snp_type:
                dna_row['snp_type'] = x.snp_type.capitalize()
            downstream_variant_dna.append(dna_row)

        if x.seq_type == 'upstream IGR':
            dna_row = { "start": x.start_index,
                        "end": x.end_index,
                        "score": x.score,
                        "variant_type": x.variant_type }
            if x.snp_type:
                dna_row['snp_type'] = x.snp_type.capitalize()
            upstream_variant_dna.append(dna_row)

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
    if data.get('downstream_format_name'):
        data['downstream_variant_data_dna'] = downstream_variant_dna
    if data.get('upstream_format_name'):
        data['upstream_variant_data_dna'] = upstream_variant_dna
    
    return data

def calculate_score(S288C_snp_seq, snp_seq, seq_length):
    count = 0
    i = 0
    for x in snp_seq:
        if i >= len(S288C_snp_seq):
            break
        if x != S288C_snp_seq[i]:
            count = count + 1
        i = i + 1
    return 1 - count/seq_length

def get_locus_id_list(query_text):

    query_list = []
    if query_text.startswith('"'):
        ## it is a go term
        term = query_text.replace('"', '').lower().replace('%20', ' ').replace('+', ' ')
        for g in DBSession.query(Go).filter(Go.display_name.ilike('%' + term + '%')).all():
            for ga in DBSession.query(Goannotation).filter_by(go_id=g.go_id, annotation_type='manually curated').all():
                query_list.append(ga.dbentity.display_name)
    else:
        query_list = query_text.split(',')
        
    locus_id_list = []
    for query in query_list:
        query = query.strip().upper()
        query = query.replace('SGD:S', 'S')
        locus = None
        if query.startswith('S00'):
            locus = DBSession.query(Dbentity).filter_by(sgdid=query).one_or_none()
            if locus is not None:
                locus_id_list.append(locus.dbentity_id)
        if locus is None:
            locus = DBSession.query(Locusdbentity).filter(or_(Locusdbentity.gene_name == query, Locusdbentity.systematic_name == query)).one_or_none()
            if locus is not None:
                locus_id_list.append(locus.dbentity_id)
                
    return locus_id_list
    
def get_protein_scores(locus_id_list, strain_to_id):
    all = []
    if len(locus_id_list) == 0:
        all = DBSession.query(Proteinsequencealignment).order_by(Proteinsequencealignment.locus_id).all()
    else:
        all = DBSession.query(Proteinsequencealignment).filter(Proteinsequencealignment.locus_id.in_(locus_id_list)).order_by(Proteinsequencealignment.locus_id).all()

    S288C_seq = None
    strain_to_seq = {}
    locus_id = None
    locus_id_to_protein_scores = {}
    
    for x in all:
        if x.locus_id != locus_id and locus_id is not None:
            scores = []
            for strain in sorted(strain_to_id, key=strain_to_id.get):
                if strain in strain_to_seq:
                    scores.append(calculate_score(S288C_seq,
                                                  strain_to_seq[strain],
                                                  len(S288C_seq)))
                else:
                    scores.append(None)
            locus_id_to_protein_scores[locus_id] = scores
            locus_id = None
            S288C_seq =	None
            strain_to_seq = {}
                                  
        if x.display_name.endswith('S288C'):
            S288C_seq = x.aligned_sequence
        locus_id = x.locus_id
        [name, strain] = x.display_name.split('_')
        strain_to_seq[strain] = x.aligned_sequence
    
    if locus_id is not None:
        scores = []
        for strain in sorted(strain_to_id, key=strain_to_id.get):
            if strain in strain_to_seq:
                scores.append(calculate_score(S288C_seq,
                                              strain_to_seq[strain],
                                              len(S288C_seq)))
            else:
                scores.append(None)
        locus_id_to_protein_scores[locus_id] = scores
    return locus_id_to_protein_scores

def get_default_scores():
    return [1, None, None, None, None, None, None, None, None, None, None, None]

def get_contig_lengths():

    CONTIG_LENGTHS = OrderedDict([
        ('I', 230218),
        ('II', 813184),
        ('III', 316620),
        ('IV',  1531933),
        ('V', 576874),
        ('VI', 270161),
        ('VII', 1090940),
        ('VIII', 562643),
        ('IX', 439888),
        ('X', 745751),
        ('XI', 666816),
        ('XII', 1078177),
        ('XIII', 924431),
        ('XIV', 784333),
        ('XV', 1091291),
        ('XVI', 94806),
        ('Mito', 85779)
    ])

    return CONTIG_LENGTHS

def get_absolute_genetic_start(contig_lengths, contig_name, start):
    chr = contig_name.replace("Chromosome ", "")
    contig_index = list(contig_lengths.keys()).index(chr)
    absolute_genetic_start = 0
    for contig in list(contig_lengths.keys()):
        if contig == chr:
            break
        absolute_genetic_start += contig_lengths[contig]
    absolute_genetic_start += start
    return absolute_genetic_start

def get_all_variant_data(request, query, offset, limit):

    locus_id_list = get_locus_id_list(query)

    if query != '' and len(locus_id_list) == 0: 
        return { "total": 0,
                 "offset": offset,
                 "loci": [] }
    
    offset = int(offset)
    limit = int(limit)
    
    taxonomy = DBSession.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
    taxonomy_id = taxonomy.taxonomy_id
    so = DBSession.query(So).filter_by(display_name='ORF').one_or_none()
    so_id = so.so_id
    dbentity_id_to_obj = dict([(x.dbentity_id, (x.sgdid, x.format_name, x.display_name)) for x in DBSession.query(Locusdbentity).all()])
    contig_id_to_display_name = dict([(x.contig_id, x.display_name) for x in DBSession.query(Contig).filter(Contig.display_name.like('Chromosome %')).all()])
    strain_to_id = strain_order()
    
    locus_id_to_protein_scores = get_protein_scores(locus_id_list, strain_to_id)

    contig_lengths = get_contig_lengths()

    all = []
    if len(locus_id_list) == 0:
        all = DBSession.query(Dnasequencealignment).filter_by(dna_type='genomic').order_by(Dnasequencealignment.locus_id).order_by(Dnasequencealignment.locus_id).all()
    else:
        all = DBSession.query(Dnasequencealignment).filter(Dnasequencealignment.locus_id.in_(locus_id_list)).filter_by(dna_type='genomic').order_by(Dnasequencealignment.locus_id).all()
        
    locus_id = None
    strain_to_snp = {}
    start = None
    seqLen = None
    S288C_snp_seq = None
    locus_id_to_data = {}
    contig_name = None
    for x in all:            
        if x.locus_id not in dbentity_id_to_obj:
            continue
        if x.locus_id != locus_id and locus_id is not None and seqLen is not None:
            (sgdid, format_name, display_name) = dbentity_id_to_obj[locus_id]
            snp_seqs = []
            dna_scores = []
            for strain in sorted(strain_to_id, key=strain_to_id.get):
                if strain in strain_to_snp:
                    snp = strain_to_snp[strain]
                    snp_seqs.append(snp)
                    dna_scores.append(calculate_score(S288C_snp_seq,
                                                      snp['snp_sequence'],
                                                      seqLen))
                else:
                    dna_scores.append(None)
            protein_scores = []
            if locus_id in locus_id_to_protein_scores:
                protein_scores = locus_id_to_protein_scores[locus_id]
            else:
                protein_scores = get_default_scores()
            data = { "absolute_genetic_start": get_absolute_genetic_start(contig_lengths, contig_name, start),
                     "href": "/locus/" +  sgdid + "/sequence#variants",
                     "sgdid": sgdid,
                     "format_name": format_name,
                     "name": display_name,
                     "snp_seqs": snp_seqs,
                     "dna_scores": dna_scores,
                     "protein_scores": protein_scores,
            }
            locus_id_to_data[locus_id] = data
            start = None
            seqLen = None
            locus_id = None
            S288C_snp_seq = None
            contig_name = None
            strain_to_snp = {}
        
        if x.display_name.endswith('S288C'):
            start = x.contig_start_index
            seqLen = len(x.aligned_sequence)
            S288C_snp_seq = x.snp_sequence
            contig_name = contig_id_to_display_name[x.contig_id]
        locus_id = x.locus_id
        [name, strain] = x.display_name.split('_')
        strain_to_snp[strain] = { "snp_sequence": x.snp_sequence,
                                  "name": strain,
                                  "id":  strain_to_id[strain] }
        
    if locus_id is not None and locus_id in dbentity_id_to_obj and seqLen is not None:
        (sgdid, format_name, display_name) = dbentity_id_to_obj[locus_id]
        snp_seqs = []
        dna_scores = []
        for strain in sorted(strain_to_id, key=strain_to_id.get):
            if strain in strain_to_snp:
                snp = strain_to_snp[strain]
                snp_seqs.append(snp)
                dna_scores.append(calculate_score(S288C_snp_seq,
                                                      snp['snp_sequence'],
                                                      seqLen))
            else:
                dna_scores.append(None)
        protein_scores = []
        if locus_id in locus_id_to_protein_scores:
            protein_scores = locus_id_to_protein_scores[locus_id]
        else:
            protein_scores = get_default_scores()
                
        data = { "absolute_genetic_start": get_absolute_genetic_start(contig_lengths, contig_name, start),
                 "href": "/locus/" +  sgdid + "/sequence#variants",
                 "sgdid": sgdid,
                 "format_name": format_name,
                 "name": display_name,
                 "snp_seqs": snp_seqs,
                 "dna_scores": dna_scores,
                 "protein_scores": protein_scores
        }
        locus_id_to_data[locus_id] = data

    loci = []
    count = 0
    index = 0
    
    all = None
    if len(locus_id_list) == 0:
        all = DBSession.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id, so_id=so_id).order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all()
    else:
        all = DBSession.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC', taxonomy_id=taxonomy_id, so_id=so_id).filter(Dnasequenceannotation.dbentity_id.in_(locus_id_list)).order_by(Dnasequenceannotation.contig_id, Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all()

    for x in all:   
        data = None
        if x.dbentity_id in locus_id_to_data:
            data = locus_id_to_data[x.dbentity_id]
        elif x.dbentity_id in dbentity_id_to_obj:
            (sgdid, format_name, display_name) = dbentity_id_to_obj[x.dbentity_id]
            contig_name = contig_id_to_display_name.get(x.contig_id)
            if contig_name is None:
                continue
            data = { "absolute_genetic_start": get_absolute_genetic_start(contig_lengths, contig_name, x.start_index),
                     "href": "/locus/" +  sgdid + "/sequence#variants",
                     "sgdid": sgdid,
                     "format_name": format_name,
                     "name": display_name,
                     "snp_seqs": [{"snp_sequence": '',
                                   "name": 'S288C',
                                   "id":  strain_to_id['S288C']}],
                     "dna_scores": get_default_scores(),
                     "protein_scores": get_default_scores()
            }
            
        if data is not None:
            # count = count + 1
            # if offset != 0 and count <= offset:
            #    continue
            # index = index + 1
            # if limit > 0 and index >= limit:
            #    break
            loci.append(data)

    variants = { "total": len(loci),
                 "offset": offset,
                 "loci": loci }
    
    return variants
