from src.helpers import upload_file
from src.boto3_upload import upload_one_file_to_s3
from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, Referencedbentity, Taxonomy, \
    Go, Ro, Eco, EcoAlias, Source, Goannotation, Goextension, \
    Gosupportingevidence, LocusAlias, Edam, Path, FilePath, Complexdbentity, \
    Filedbentity, ReferenceAlias, Dnasequenceannotation, So, ComplexAlias
from urllib.request import urlretrieve
from urllib.request import urlopen
from datetime import datetime
import logging
import os
import sys
import gzip
import importlib
importlib.reload(sys)  # Reload does the trick!


__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

gaf_file = "scripts/dumping/curation/data/gene_association.sgd"
go_central_url = "http://release.geneontology.org/"
gaf_from_go = "sgd.gaf.gz"

namespace_to_code = {"biological process": 'P',
                     "molecular function": 'F',
                     "cellular component": 'C'}

so_to_col12 = {"ORF": "protein",
               "transposable element gene": "protein",
               "blocked reading frame": "protein",
               "disabled reading frame": "protein",
               "pseudogene": "protein",
               "ncRNA gene": "ncRNA",
               "snoRNA gene": "snoRNA",
               "snRNA gene": "snRNA",
               "tRNA gene": "tRNA",
               "rRNA gene": "rRNA",
               "telomerase RNA gene": "telomerase_RNA"}

DBID = 0
NAME = 1
QUALIFIER = 2
GOID = 3
REFERENCE = 4
EVIDENCE = 5
SUPPORT_EVIDENCE = 6
ASPECT = 7
HEADLINE = 8
ALIAS = 9
TAG = 10
TAXON = 11
DATE = 12
SOURCE = 13
ANNOT_TYPE = 14  # for yeastmine
LAST_FIELD = 13

DATABASE = 'Saccharomyces Genome Database (SGD)'
URL = 'http://www.yeastgenome.org/'
EMAIL = 'sgd-helpdesk@lists.stanford.edu'
FUNDING = 'NHGRI at US NIH, grant number U41 HG001315'
DB = 'SGD'
TAXON_ID = '559292'
COMPLEX_NAME_TYPE = 'protein_complex'
DEFAULT_NAME_TYPE = 'gene'

def dump_data(noctua_gpad_file):

    nex_session = get_session()

    fw = open(gaf_file, "w")

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    write_header(fw, datestamp)

    log.info(str(datetime.now()))
    log.info("Getting data from the database...")

    id_to_source = dict([(x.source_id, x.display_name)
                         for x in nex_session.query(Source).all()])
    source_to_id = dict([(x.display_name, x.source_id)
                         for x in nex_session.query(Source).all()])
    id_to_gene = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.headline, x.qualifier))
                       for x in nex_session.query(Locusdbentity).all()])

    id_to_complex = dict([(x.dbentity_id, (x.format_name, x.display_name))
                       for x in nex_session.query(Complexdbentity).all()])

    id_to_go = dict([(x.go_id, (x.goid, x.display_name, x.go_namespace))
                     for x in nex_session.query(Go).all()])
    id_to_pmid = dict([(x.dbentity_id, x.pmid)
                       for x in nex_session.query(Referencedbentity).all()])
    id_to_uniprot = dict([(x.locus_id, x.display_name)
                       for x in nex_session.query(LocusAlias).filter_by(alias_type='UniProtKB ID').all()])
    id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(
        Dbentity).filter(Dbentity.subclass.in_(['REFERENCE', 'LOCUS', 'COMPLEX'])).all()])
    id_to_ecoid = dict([(x.eco_id, x.format_name)
                        for x in nex_session.query(Eco).all()])
    id_to_taxon = dict([(x.taxonomy_id, x.taxid)
                        for x in nex_session.query(Taxonomy).all()])
    id_to_ro = dict([(x.ro_id, x.display_name)
                     for x in nex_session.query(Ro).all()])
    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in nex_session.query(Edam).all()])
    id_to_go_ref = dict([(x.reference_id, x.display_name) for x in nex_session.query(
        ReferenceAlias).filter(ReferenceAlias.display_name.like('GO_REF:%')).all()])
    so_id_to_term = dict([(x.so_id, x.display_name)
                          for x in nex_session.query(So).all()])
    S288C_row = nex_session.query(Taxonomy).filter_by(
        format_name='Saccharomyces_cerevisiae_S288c').one_or_none()
    S288C_taxonomy_id = S288C_row.taxonomy_id

    id_to_eco = {}
    for x in nex_session.query(EcoAlias).all():
        if len(x.display_name) > 5:
            continue
        id_to_eco[x.eco_id] = x.display_name

    id_to_alias_list = {}
    for x in nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(['Uniform', 'Non-uniform', 'NCBI protein name'])).all():
        alias_list = ''
        if x.locus_id in id_to_alias_list:
            alias_list = id_to_alias_list[x.locus_id] + "|" + x.display_name
        else:
            alias_list = x.display_name
        id_to_alias_list[x.locus_id] = alias_list
        
    for x in nex_session.query(ComplexAlias).all():
        alias_list = ''
        if x.complex_id in id_to_alias_list:
             alias_list = id_to_alias_list[x.complex_id] + "|" + x.display_name
        else:
            alias_list = x.display_name
        id_to_alias_list[x.complex_id] = alias_list
        
    locus_id_to_col12 = {}
    for x in nex_session.query(Dnasequenceannotation).filter_by(dna_type='GENOMIC').all():
        so_term = so_id_to_term[x.so_id]
        col12 = so_to_col12.get(so_term)
        if col12 is not None:
            if x.dbentity_id not in locus_id_to_col12:
                locus_id_to_col12[x.dbentity_id] = col12
            elif col12 != locus_id_to_col12[x.dbentity_id] and x.taxonomy_id == S288C_taxonomy_id:
                locus_id_to_col12[x.dbentity_id] = col12

    annotation_id_to_extensions = {}
    group_id_to_extensions = {}
    pre_annot_id = 0
    for x in nex_session.query(Goextension).order_by(Goextension.annotation_id, Goextension.group_id.asc()).all():
        if pre_annot_id != x.annotation_id and pre_annot_id != 0:
            annotation_id_to_extensions[pre_annot_id] = group_id_to_extensions
            group_id_to_extensions = {}
        extensions = []
        if x.group_id in group_id_to_extensions:
            extensions = group_id_to_extensions[x.group_id]
        extensions.append(id_to_ro[x.ro_id].replace(
            " ", "_")+'(' + x.dbxref_id + ')')
        group_id_to_extensions[x.group_id] = extensions
        pre_annot_id = x.annotation_id

    annotation_id_to_evidences = {}
    group_id_to_evidences = {}
    pre_annot_id = 0
    for x in nex_session.query(Gosupportingevidence).order_by(Gosupportingevidence.annotation_id, Gosupportingevidence.group_id.asc()).all():
        if pre_annot_id != x.annotation_id and pre_annot_id != 0:
            annotation_id_to_evidences[pre_annot_id] = group_id_to_evidences
            group_id_to_evidences = {}
        evidences = []
        if x.group_id in group_id_to_evidences:
            evidences = group_id_to_evidences[x.group_id]
        evidences.append(x.dbxref_id)
        group_id_to_evidences[x.group_id] = evidences
        pre_annot_id = x.annotation_id

    loaded = {}

    noctuaData = read_noctua_data(noctua_gpad_file)

    for x in nex_session.query(Goannotation).all():

        row = [None] * (LAST_FIELD+1)

        feature_name = None
        gene_name = None
        name_type = None
        headline = ''
        qualifier = ''
        if x.dbentity_id in id_to_gene:
            (feature_name, gene_name, headline, qualifier) = id_to_gene[x.dbentity_id]
            name_type = locus_id_to_col12.get(x.dbentity_id)
            if name_type is None:
                name_type = DEFAULT_NAME_TYPE
            if gene_name is None:
                gene_name = feature_name
            if headline:
                headline = headline.strip()
            row[NAME] = gene_name
            if headline:
                row[HEADLINE] = headline
            else:
                row[HEADLINE] = ''
        elif x.dbentity_id in id_to_complex:
            (complexAcc, complexNm) = id_to_complex[x.dbentity_id]
            feature_name = complexNm
            row[NAME] = complexAcc
            row[HEADLINE] = ''
            name_type = COMPLEX_NAME_TYPE
        else:
            print ("UNKNOWN object: ", x.annotation_id, x.dbentity_id)
            continue
          
        row[DBID] = id_to_sgdid[x.dbentity_id]

        alias_list = id_to_alias_list.get(x.dbentity_id)
        if alias_list is None:
            alias_list = feature_name
        else:
            alias_list = feature_name + "|" + alias_list
        row[ALIAS] = alias_list

        (goid, go_term, go_aspect) = id_to_go[x.go_id]
        row[GOID] = goid

        # reference = "SGD_REF:" + id_to_sgdid[x.reference_id]
        # if id_to_pmid.get(x.reference_id) is not None:
        #    reference = reference + "|" + "PMID:" + str(id_to_pmid.get(x.reference_id))
        reference = ""
        if id_to_pmid.get(x.reference_id) is not None:
            reference = "PMID:" + str(id_to_pmid.get(x.reference_id))
        else:
            reference = id_to_go_ref[x.reference_id]
        row[REFERENCE] = reference

        go_qualifier = x.go_qualifier
        
        if go_qualifier.startswith('NOT'):
            if go_aspect == 'cellular component':
                go_qualifier = 'NOT|part_of'
            elif go_aspect == 'biological process':
                go_qualifier = 'NOT|involved_in'
            else:
                go_qualifier = 'NOT|enables'
                
        # go_qualifier = x.go_qualifier.replace('acts upstream of or within ', 'acts upstream of or within, ')
        go_qualifier = go_qualifier.replace(' ', '_')
        
        row[QUALIFIER] = go_qualifier
        row[ASPECT] = namespace_to_code[go_aspect]

        eco_code = id_to_eco.get(x.eco_id)
        if eco_code is None:
            if x.eco.display_name.startswith('biological system reconstruction '):
                eco_code = 'BSR'
            else:
                print ("UNKNOWN eco_code", x.annotation_id, x.eco_id)
                continue
        if eco_code == 'IMR':
            eco_code = "IKR"
        row[EVIDENCE] = eco_code

        ### check if the annotation is in nochua list. If yes, exclude it.
        key = (row[DBID], row[GOID], row[REFERENCE],
               id_to_ecoid[x.eco_id], x.annotation_type)
        if key in noctuaData:
            evidences = annotation_id_to_evidences.get(
                x.annotation_id, {}).get(1, [])
            extensions = annotation_id_to_extensions.get(
                x.annotation_id, {}).get(1, [])
            evidences.sort()
            extensions.sort()
            (noctua_qualifier, noctua_evidences,
             noctua_extensions) = noctuaData[key]
            if noctua_qualifier == row[QUALIFIER] and noctua_evidences == ','.join(evidences) and noctua_extensions == ','.join(extensions):
                continue

        source = id_to_source[x.source_id]
        row[SOURCE] = source

        date_created = x.date_created
        if eco_code == 'IEA' or (eco_code in ['IBA', 'IRD', 'IKR'] and source == 'GO_Central'):
            date_created = x.date_assigned
        row[DATE] = str(date_created).split(' ')[0].replace("-", "")
        row[TAXON] = "taxon:" + TAXON_ID
        row[TAG] = name_type

        all_support_evidences = {"1": []}
        if x.annotation_id in annotation_id_to_evidences:
            all_support_evidences = annotation_id_to_evidences[x.annotation_id]

        all_extensions = {"1": []}
        if x.annotation_id in annotation_id_to_extensions:
            all_extensions = annotation_id_to_extensions[x.annotation_id]

        found = {}

        gpID = id_to_uniprot.get(x.dbentity_id, '')
        if gpID:
            gpID = "UniProtKB:" + gpID
        
        for evid_group_id in sorted(all_support_evidences.keys()):
            support_evidences = ",".join(all_support_evidences[evid_group_id])
            for ext_group_id in sorted(all_extensions.keys()):
                extensions = ",".join(all_extensions[ext_group_id])
                if (support_evidences, extensions) in found:
                    continue
                found[(support_evidences, extensions)] = 1
                if qualifier != 'Dubious':
                    fw.write(DB + "\t")
                for i in range(0, LAST_FIELD+1):
                    if i == 6:
                        if qualifier != 'Dubious':
                            fw.write(support_evidences + "\t")
                    else:
                        if qualifier != 'Dubious':
                            fw.write(str(row[i]) + "\t")

                    if i == LAST_FIELD:
                        if qualifier != 'Dubious':
                            fw.write(extensions + "\t" + gpID + "\n")

    fw.close()

    log.info("Uploading GAF file to S3...")

    update_database_load_file_to_s3(
        nex_session, gaf_file, True, source_to_id, edam_to_id, datestamp)

    nex_session.close()

    ##### download sgd gaf from go central and upload it to S3
    download_sgd_gaf_from_go_central()
    local_file = open(gaf_from_go, mode='rb')
    upload_one_file_to_s3(local_file, "latest/" + gaf_from_go)
    ## done

    log.info(str(datetime.now()))
    log.info("Done!")

    
def write_header(fw, datestamp):

    fw.write("!gaf-version: 2.2\n")
    fw.write("!date-generated: " + datestamp + "\n")
    fw.write("!generated-by: Saccharomyces Genome Database (SGD)\n")
    fw.write("!URL: https://www.yeastgenome.org/\n")
    fw.write("!Contact Email: sgd-helpdesk@lists.stanford.edu\n")
    fw.write("!Funding: NHGRI at US NIH, grant number U41-HG001315\n")
    fw.write("!\n")
    
def download_sgd_gaf_from_go_central():

    sgd_gaf_url = "http://current.geneontology.org/annotations/sgd.gaf.gz"
    urlretrieve(sgd_gaf_url, gaf_from_go)
    
def update_database_load_file_to_s3(nex_session, gaf_file, is_public, source_to_id, edam_to_id, datestamp):

    # gene_association.sgd.20171204.gaf.gz
    # gene_association.sgd-yeastmine.20171204.gaf.gz

    # datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
    gzip_file = gaf_file + "." + datestamp + ".gaf.gz"
    import gzip
    import shutil
    with open(gaf_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    local_file = open(gzip_file, mode='rb')

    ### upload a current GAF file to S3 with a static URL for Go Community ###
    # if is_public == 'true':
    #    upload_gaf_to_s3(local_file, "latest/gene_association.sgd.gaf.gz")
    ##########################################################################

    import hashlib
    gaf_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(
        md5sum=gaf_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")

    if is_public == True:
        nex_session.query(Dbentity).filter(Dbentity.display_name.like('gene_association.sgd%')).filter(
            Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
        nex_session.commit()

    data_id = edam_to_id.get('EDAM:2048')  # data:2048 Report
    topic_id = edam_to_id.get('EDAM:0085')  # topic:0085 Functional genomics
    format_id = edam_to_id.get('EDAM:3475')  # format:3475 TSV

    if "yeastmine" not in gaf_file:
        from sqlalchemy import create_engine
        from src.models import DBSession
        engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
        DBSession.configure(bind=engine)

    readme = nex_session.query(Dbentity).filter_by(
        display_name="gene_association.README", dbentity_status='Active').one_or_none()
    if readme is None:
        log.info("gene_association.README is not in the database.")
        return
    readme_file_id = readme.dbentity_id

    # path.path = /reports/function

    upload_file(CREATED_BY, local_file,
                filename=gzip_file,
                file_extension='gz',
                description='All GO annotations for yeast genes (protein and RNA) in GAF file format',
                display_name=gzip_file,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                readme_file_id=readme_file_id,
                is_public=is_public,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_to_id['SGD'],
                md5sum=gaf_md5sum)

    gaf = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()
    if gaf is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = gaf.dbentity_id

    path = nex_session.query(Path).filter_by(
        path="/reports/function").one_or_none()
    if path is None:
        log.info("The path /reports/function is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_to_id['SGD'],
                 created_by=CREATED_BY)

    nex_session.add(x)
    nex_session.commit()

    log.info("Done uploading " + gaf_file)


def read_noctua_data(noctua_gpad_file):

    f = None
    if noctua_gpad_file.endswith('.gz'):
        f = gzip.open(noctua_gpad_file, 'rt')
    else:
        f = open(noctua_gpad_file)

    read_line = {}
    data = {}
    for line in f:
        if line.startswith('!'):
            continue
        field = line.strip().split('\t')

        ## get rid of duplicate lines...
        if line in read_line:
            continue
        read_line[line] = 1
        sgdid = field[1]
        go_qualifier = field[2]
        if 'NOT' in go_qualifier:
            go_qualifier = 'NOT'
        if go_qualifier not in ['NOT', 'contributes_to', 'colocalizes_with']:
            go_qualifier = ''
        goid = field[3]
        eco = field[5]
        pmid = field[4].replace(' ', '')
        annotation_type = 'manually curated'
        key = (sgdid, goid, pmid, eco, annotation_type)
        evidences = field[6].split(',')
        evidences.sort()
        extensions = field[10].split(',')
        extensions.sort()
        data[key] = (go_qualifier, ','.join(evidences), ','.join(extensions))

    return data


if __name__ == '__main__':

    noctua_path = 'http://snapshot.geneontology.org/products/upstream_and_raw_data/'
    noctua_gpad_file = 'noctua_sgd.gpad.gz'
    urlretrieve(noctua_path + noctua_gpad_file, noctua_gpad_file)

    dump_data(noctua_gpad_file)
