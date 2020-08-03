from src.models import Locusdbentity, Dbentity, Geninteractionannotation, Referencedbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'

nex_session = get_session()

locus_id_to_names =  dict([(x.dbentity_id, (x.systematic_name, x.gene_name)) for x in nex_session.query(Locusdbentity).all()])

allele_to_id = dict([(x.display_name.upper(), x.dbentity_id) for x in nex_session.query(Dbentity).filter_by(subclass='ALLELE').all()])

reference_id_to_pmid =  dict([(x.dbentity_id, x.pmid) for x in nex_session.query(Referencedbentity).all()])

all = nex_session.query(Geninteractionannotation).filter(Geninteractionannotation.description.like('%allele%')).all()

allele_to_skip = {}
f = open("scripts/loading/allele/data/genInteractionAlleles2NOTload072020.tsv")
for line in f:
    allele_to_skip[line.strip().upper()] = 1
f.close()
    
for x in all:
    (orf, gene) = locus_id_to_names.get(x.dbentity1_id)
    (orf2, gene2) = locus_id_to_names.get(x.dbentity2_id)
    if gene is None:
        gene = orf
    if gene2 is None:
        gene2 = orf2
        
    words = x.description.split(' ')
    found = {}
    for word in words:
        if len(word) < 4:
            continue
        if word[-1] in [')', ',', '/', '|', ';', ':', '.']:
            word = word[0:-2]
        if word[0] in ['(', '/', '|']:
            word = word[1:]

        if word in found:
            continue
        found[word] = 1
        if  word.upper() in allele_to_skip:
            continue
        
        if word.upper() not in [orf.upper(), gene.upper(), orf2.upper(), gene2.upper()]:
            allele = word
            matching_gene = None
            if word.upper().startswith(orf.upper()):
                matching_gene = orf
            elif word.upper().startswith(gene.upper()):
                matching_gene =	gene
            elif word.upper().startswith(orf2.upper()):
                matching_gene = orf2
            elif word.upper().startswith(gene2.upper()):
                matching_gene = gene2
            if matching_gene is not None:
                pmid = reference_id_to_pmid.get(x.reference_id)
                print (allele + "\t" + matching_gene + "\t" + str(x.annotation_id) + "\t" + gene + "/" + orf + "\t" + gene2 + "/" + orf2 + "\t" + str(pmid) + "\t" + x.description + "\t" + str(x.date_created).split(' ')[0])
                
nex_session.close()

exit
