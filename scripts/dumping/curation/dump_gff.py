from src.helpers import upload_file
from scripts.loading.database_session import get_session
from src.models import Dbentity, Locusdbentity, LocusAlias, Dnasequenceannotation, \
    Dnasubsequence, So, Contig, Go, Goannotation, Ro, Edam, Path, LocusRelation, \
    FilePath, Filedbentity, Source, Transcriptdbentity, TranscriptReference
import shutil
import gzip
from datetime import datetime
import logging
import os
import sys
import re
import importlib
importlib.reload(sys)  # Reload does the trick!

__author__ = 'sweng66'

# Handlers need to be reset for use under Fargate. See
# https://stackoverflow.com/questions/37703609/using-python-logging-with-aws-lambda/56579088#56579088
# for details.  Applies to Fargate in addition to Lambda.

log = logging.getLogger()
if log.handlers:
    for handler in log.handlers:
        log.removeHandler(handler)

logging.basicConfig(
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ],
    level=logging.INFO
)

CREATED_BY = os.environ['DEFAULT_USER']

gff_file = "scripts/dumping/curation/data/saccharomyces_cerevisiae.gff"
landmark_file = "scripts/dumping/curation/data/landmark_gene.txt"

chromosomes = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX',
               'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'Mito']


def dump_data():

    nex_session = get_session()

    fw = open(gff_file, "w")

    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")

    write_header(fw, str(datetime.now()))

    log.info(str(datetime.now()))
    log.info("Getting edam, so, source, & sgdid  data from the database...")

    locus_id_to_uniprot = dict([(x.locus_id, x.display_name) for x in nex_session.query(
        LocusAlias).filter_by(alias_type='UniProtKB ID').all()])

    locus_id_to_refseq = dict([(x.locus_id, x.display_name) for x in nex_session.query(
        LocusAlias).filter_by(alias_type='RefSeq nucleotide version ID').all()])

    log.info("num uniprot ids:" + str(len(locus_id_to_uniprot.keys())))
    log.info("num refseq ids:" + str(len(locus_id_to_refseq.keys())))

    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in nex_session.query(Edam).all()])
    source_to_id = dict([(x.display_name, x.source_id)
                         for x in nex_session.query(Source).all()])
    so_id_to_so = dict([(x.so_id, x)
                               for x in nex_session.query(So).all()])
    # so = nex_session.query(So).filter_by(display_name='gene').one_or_none()
    # gene_soid = so.soid

    ro = nex_session.query(Ro).filter_by(display_name='part of').one_or_none()
    child_id_to_parent_id = dict([(x.child_id, x.parent_id)
                                  for x in nex_session.query(LocusRelation).filter_by(ro_id=ro.ro_id).all()])
    
    locus_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in nex_session.query(
        Dbentity).filter_by(subclass='LOCUS', dbentity_status='Active').all()])

    log.info(str(datetime.now()))
    log.info("Getting alias data from the database...")

    alias_data = nex_session.query(LocusAlias).filter(LocusAlias.alias_type.in_(
        ['Uniform', 'Non-uniform', 'NCBI protein name'])).all()

    locus_id_to_aliases = {}
    for x in alias_data:
        aliases = []
        if x.locus_id in locus_id_to_aliases:
            aliases = locus_id_to_aliases[x.locus_id]
        aliases.append(do_escape(x.display_name))
        locus_id_to_aliases[x.locus_id] = aliases

    log.info(str(datetime.now()))
    log.info("Getting locus data from the database...")

    locus_id_to_info = dict([(x.dbentity_id, (x.systematic_name, x.gene_name, x.qualifier, x.headline, x.description))
                             for x in nex_session.query(Locusdbentity).filter_by(has_summary='1').all()])

    log.info(str(datetime.now()))
    log.info("Getting go annotation data from the database...")

    go_id_to_goid = dict([(x.go_id, x.goid)
                          for x in nex_session.query(Go).all()])

    go_data = nex_session.query(Goannotation).filter(
        Goannotation.annotation_type != 'computational').all()

    locus_id_to_goids = {}
    for x in go_data:
        goid = go_id_to_goid[x.go_id]
        goids = []
        if x.dbentity_id in locus_id_to_goids:
            goids = locus_id_to_goids[x.dbentity_id]
        goids.append(goid)
        locus_id_to_goids[x.dbentity_id] = goids

    log.info(str(datetime.now()))
    log.info("Getting chromosome data from the database...")

    # check curators to see what should we set for chr dbxref ID? SGDID or
    # GenBank Accession (eg, BK006935.2) or RefSeq ID (eg, NC_001133.9)
    format_name_list = ["Chromosome_" + x for x in chromosomes]
    chr_to_contig = dict([(x.format_name.replace("Chromosome_", ""), (x.contig_id, x.genbank_accession, len(
        x.residues))) for x in nex_session.query(Contig).filter(Contig.format_name.in_(format_name_list)).all()])
    chr_to_seq = dict([(x.format_name.replace("Chromosome_", ""), x.residues) for x in nex_session.query(
        Contig).filter(Contig.format_name.in_(format_name_list)).all()])

    log.info(str(datetime.now()))
    log.info("Getting dnasequenceannotation/dnasubsequence data from the database...")

    subfeature_data = nex_session.query(Dnasubsequence).order_by(
        Dnasubsequence.contig_start_index, Dnasubsequence.contig_end_index).all()

    landmark_gene = get_landmark_genes()

    ## get transcript data in database ##
    log.info(str(datetime.now()))
    log.info("Getting transcript data from the database...")

    systematic_name_to_transcripts = {}
    transcripts = nex_session.query(
        Dbentity).filter_by(subclass='TRANSCRIPT').all()

    log.info("num of transcript objs: " + str(len(transcripts)))

   # make dict of transcripts to systematic name
    for transcriptObj in transcripts:
        transSeqAnnot = nex_session.query(Dnasequenceannotation).filter_by(
            dbentity_id=transcriptObj.dbentity_id).first()
        sysName = transcriptObj.format_name.split("_")[0]
        #log.info(sysName + " has transcript " + transcriptObj.display_name)

        transcriptConds = nex_session.query(Transcriptdbentity).filter_by(
            dbentity_id=transcriptObj.dbentity_id).first()

        tconditions = []
        # log.info("YPD:" + str(transcriptConds.in_ypd) +
        #         " GAL" + str(transcriptConds.in_gal))
        if str(transcriptConds.in_ypd) == 'True':
            tconditions.append('YPD')
        #    log.info("in YPD")
        if str(transcriptConds.in_gal) == 'True':
            tconditions.append('GAL')
        #    log.info("in GAL")

        transSeqAnnot_strand = transSeqAnnot.strand
        if transSeqAnnot_strand == '0':
            transSeqAnnot_strand = '.'
            
        if sysName in systematic_name_to_transcripts.keys():
            systematic_name_to_transcripts[sysName].append({"sgdid": "SGD:" + transcriptObj.sgdid,
                                                            "name": transcriptObj.format_name,
                                                            "start": transSeqAnnot.start_index,
                                                            "end": transSeqAnnot.end_index,
                                                            "contig": transSeqAnnot.contig,
                                                            "strand": transSeqAnnot_strand,
                                                            "conditions": ",".join(tconditions)})
        else:
            systematic_name_to_transcripts[sysName] = [{"sgdid": "SGD:" + transcriptObj.sgdid,
                                                        "name": transcriptObj.format_name,
                                                        "start": transSeqAnnot.start_index,
                                                        "end": transSeqAnnot.end_index,
                                                        "contig": transSeqAnnot.contig,
                                                        "strand": transSeqAnnot_strand,
                                                        "conditions": ",".join(tconditions)}]

    for chr in chromosomes:

        (contig_id, accession_id, length) = chr_to_contig[chr]

        if chr == 'Mito':
            chr = 'mt'

        fw.write("chr" + chr + "\tSGD\tchromosome\t1\t" + str(length) + "\t.\t.\t.\tID=chr" +
                 chr + ";dbxref=NCBI:" + accession_id + ";Name=chr" + chr + "\n")

        # get features for each contig_id
        # print features in the order of chromosome and coord

        gene_data = nex_session.query(Dnasequenceannotation).filter_by(contig_id=contig_id, dna_type='GENOMIC').order_by(
            Dnasequenceannotation.start_index, Dnasequenceannotation.end_index).all()

        annotation_id_to_subfeatures = {}
        UTRs = {}
        for x in subfeature_data:
            subfeatures = []
            if x.annotation_id in annotation_id_to_subfeatures:
                subfeatures = annotation_id_to_subfeatures[x.annotation_id]
            subfeatures.append(
                (x.display_name, x.contig_start_index, x.contig_end_index))
            annotation_id_to_subfeatures[x.annotation_id] = subfeatures
            if x.display_name == 'five_prime_UTR_intron':
                UTRs[x.annotation_id] = (
                    x.contig_start_index, x.contig_end_index)

        for x in gene_data:
            uniprotid = str()
            refseqid = str()
            if x.dbentity_id not in locus_id_to_sgdid:
                # deleted or merged
                continue

            sgdid = "SGD:" + locus_id_to_sgdid[x.dbentity_id]

            if x.dbentity_id in locus_id_to_uniprot.keys():
                uniprotid = "UniProtKB:" + locus_id_to_uniprot[x.dbentity_id]
                log.info("uniprot id:" + uniprotid)
            if x.dbentity_id in locus_id_to_refseq.keys():
                refseqid = "RefSeq:" + locus_id_to_refseq[x.dbentity_id]
                log.info("has refseq:" + refseqid)

            # type = so_id_to_term_name[x.so_id]
            so = so_id_to_so[x.so_id]
            type = so.term_name
            if type == 'ORF':
                type = 'gene'
            if type == 'gene_group':
                continue

            strand = x.strand
            if strand == '0':
                strand = '.'
                
            (systematic_name, gene_name, qualifier, headline,
             description) = locus_id_to_info[x.dbentity_id]

            if systematic_name in landmark_gene:
                fw.write("chr" + chr + "\tlandmark\tregion\t" + str(x.start_index) + "\t" + str(
                    x.end_index) + "\t.\t" + strand + "\t.\tID=" + landmark_gene[systematic_name] + "\n")

            alias_list = None
            if x.dbentity_id in locus_id_to_aliases:
                aliases = sorted(locus_id_to_aliases[x.dbentity_id])
                alias_list = ",".join(aliases)
            if gene_name:
                gene_name = do_escape(gene_name)
                if alias_list:
                    alias_list = gene_name + "," + alias_list
                else:
                    alias_list = gene_name
            systematic_name = do_escape(systematic_name)
            start_index = x.start_index
            end_index = x.end_index
            if x.annotation_id in UTRs:
                (utrStart, utrEnd) = UTRs[x.annotation_id]
                if utrStart < start_index:
                    start_index = utrStart
                else:
                    end_index = utrEnd

            fw.write("chr" + chr + "\tSGD\t" + type + "\t" + str(start_index) + "\t" + str(end_index) +
                     "\t.\t" + strand + "\t.\tID=" + systematic_name + ";Name=" + systematic_name)

            if type == "transposable_element_gene":
                parent_dbentity_id = child_id_to_parent_id.get(x.dbentity_id)
                if parent_dbentity_id and parent_dbentity_id in locus_id_to_info:
                    (parent_systematic_name, parent_gene_name, parent_qualifier,
                     parent_headline, parent_description) = locus_id_to_info[parent_dbentity_id]
                    fw.write(";Parent=" + parent_systematic_name)
                    
            if gene_name:
                fw.write(";gene=" + gene_name)
            if type == 'gene':
                fw.write(";so_term_name=protein_coding_gene")
            if alias_list:
                fw.write(";Alias=" + alias_list)
            if x.dbentity_id in locus_id_to_goids:
                goids = sorted(locus_id_to_goids[x.dbentity_id])
                goid_list = ",".join(goids)
                fw.write(";Ontology_term=" + goid_list + "," + so.soid)
            if description:
                fw.write(";Note=" + do_escape(description))
            if headline:
                fw.write(";display=" + do_escape(headline))

            fw.write(";dbxref=" + sgdid)

            if qualifier:
                fw.write(";orf_classification=" + qualifier)

            # keep this curie=, already in the GFF file for gene rows before  11/17/2020#
            fw.write(";curie=" + sgdid + "\n")

            if x.annotation_id not in annotation_id_to_subfeatures or type in ['pseudogene']:
                continue

            subfeatures = annotation_id_to_subfeatures.get(x.annotation_id)

            start2phase = get_phase(subfeatures, x.strand)

            telomeric_repeat_index = {}

            has_subfeature = 0
            for (display_name, contig_start_index, contig_end_index) in subfeatures:

                if display_name == 'non_transcribed_region':
                    continue

                name = systematic_name + "_" + display_name

                if systematic_name.startswith("TEL") and display_name == 'telomeric_repeat':
                    index = 1
                    if name in telomeric_repeat_index:
                        index = telomeric_repeat_index[name] + 1
                    telomeric_repeat_index[name] = index
                    name = name + "_" + str(index)

                phase = "."
                if display_name == 'CDS':
                    phase = start2phase[contig_start_index]

                parent = systematic_name
                if type == 'gene':  # check for expt transcript
                    if systematic_name in systematic_name_to_transcripts.keys():
                        log.info(systematic_name + " has a DB transcript")
                        parentList = list()

                        for transcript in systematic_name_to_transcripts[systematic_name]:
                            # if re.search("YPD", transcript["conditions"]):
                            parentList.append(transcript["name"])

                        parent = ",".join(parentList)
                        #parent = transcript["name"]
                        #  log.info(systematic_name +
                        #           " CDS parent: " + parent)
                        #      break
                    else:
                        parent = systematic_name + "_mRNA"                    
                elif type.endswith('_gene') and type != 'transposable_element_gene':
                    rnaType = type.replace("_gene", "")
                    parent = systematic_name + "_" + rnaType

                has_subfeature = 1

                fw.write("chr" + chr + "\tSGD\t" + display_name + "\t" + str(contig_start_index) + "\t" + str(
                    contig_end_index) + "\t.\t" + strand + "\t" + str(phase) + "\tParent=" + parent + ";Name=" + name)
                if type == 'gene' and qualifier:
                    fw.write(";orf_classification=" + qualifier)
                 # FOR Alliance ##
                if display_name == 'CDS' and uniprotid != "":
                    fw.write(";protein_id="+uniprotid)
                fw.write("\n")

                # fw.write("chr" + chr + "\tSGD\t" + display_name + "\t" + str(contig_start_index) + "\t" + str(contig_end_index) + "\t.\t" + strand + "\t" + str(phase) + "\tID=" + name + ";Name=" + name + ";dbxref=" + sgdid + ";curie=" + sgdid + "\n");

            if type == 'gene':
                if systematic_name in systematic_name_to_transcripts.keys():
                    for each in systematic_name_to_transcripts[systematic_name]:
                        if refseqid != "":
                            fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(each["start"]) + "\t" + str(each["end"]) + "\t.\t" + each["strand"] + "\t.\tID=" + each["name"] +
                                     ";Name=" + each["name"] + ";Parent=" + systematic_name + ";transcript_id=" + each["sgdid"] + ";dbxref=" + refseqid+";conditions=" + each["conditions"]+"\n")
                        else:
                            fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(each["start"]) + "\t" + str(each["end"]) + "\t.\t" + each["strand"] + "\t.\tID=" + each["name"] + ";Name=" +
                                     each["name"] + ";Parent=" + systematic_name + ";transcript_id=" + each["sgdid"] + ";conditions=" + each["conditions"] + "\n")
                else:
                    if refseqid != "":
                        fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(start_index) + "\t" + str(end_index) + "\t.\t" + strand + "\t.\tID=" + systematic_name +
                                 "_mRNA;Name=" + systematic_name + "_mRNA;Parent=" + systematic_name + ";transcript_id="+refseqid + "\n")
                    else:
                        fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(start_index) + "\t" + str(end_index) + "\t.\t" + strand +
                                 "\t.\tID=" + systematic_name + "_mRNA;Name=" + systematic_name + "_mRNA;Parent=" + systematic_name + "\n")

            elif has_subfeature == 1:
                if type != "transposable_element_gene":
                    rnaType = type.replace("_gene", "")
                    fw.write("chr" + chr + "\tSGD\t" + rnaType + "\t" + str(start_index) + "\t" +
                             str(end_index) + "\t.\t" + strand + "\t.\tID=" +
                             systematic_name + "_" + rnaType + ";Name=" + systematic_name +
                             "_" + rnaType + ";Parent=" + systematic_name + "\n")
                
    # output 17 chr sequences at the end

    fw.write("###\n")
    fw.write("##FASTA\n")

    for chr in chromosomes:
        seq = chr_to_seq[chr]
        if chr == 'Mito':
            chr = 'mt'
        fw.write(">chr" + chr + "\n")
        formattedSeq = formated_seq(seq)
        fw.write(formattedSeq + "\n")

    fw.close()

# make gzip file

    gzip_file = gzip_gff_file(gff_file, datestamp)

    log.info("Uploading gff3 file to S3...")

    update_database_load_file_to_s3(
        nex_session, gff_file, gzip_file, source_to_id, edam_to_id)

    nex_session.close()

    log.info(str(datetime.now()))
    log.info("Done!")


def formated_seq(sequence):

    return "\n".join([sequence[i:i+80] for i in range(0, len(sequence), 80)])


def get_landmark_genes():

    landmark_gene = {}

    f = open(landmark_file)
    for line in f:
        pieces = line.strip().split("\t")
        landmark_gene[pieces[1]] = pieces[0]
    f.close()

    return landmark_gene


def get_phase(subfeatures, strand):

    if strand == '-':
        subfeatures.reverse()

    length = 0
    start2phase = {}
    for (display_name, contig_start_index, contig_end_index) in subfeatures:
        if display_name != 'CDS':
            continue
        phase = length % 3
        if phase != 0:
            phase = 3 - phase
        start2phase[contig_start_index] = phase
        length += contig_end_index - contig_start_index + 1

    return start2phase


def do_escape(text):

    text = text.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
    text = text.replace(",", "%2C")
    text = text.replace(";", "%3B")
    text = text.replace('“', '"').replace('”', '"').replace("’", "'")
    text = text.replace('α', 'alpha').replace('β', 'beta')
    text = text.replace('=', '%3D')
    text = text.rstrip()
    return text


def gzip_gff_file(gff_file, datestamp):

    # gff_file  = saccharomyces_cerevisiae.gff
    # gzip_file = saccharomyces_cerevisiae.20170114.gff.gz
    gzip_file = gff_file.replace(".gff", "") + "." + datestamp + ".gff.gz"

    with open(gff_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    return gzip_file


def update_database_load_file_to_s3(nex_session, gff_file, gzip_file, source_to_id, edam_to_id):

    local_file = open(gzip_file, mode='rb')

    ### upload a current GFF file to S3 with a static URL for Go Community ###
    # upload_gff_to_s3(local_file, "latest/saccharomyces_cerevisiae.gff.gz")
    ##########################################################################

    import hashlib
    gff_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = nex_session.query(Filedbentity).filter_by(
        md5sum=gff_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")

    nex_session.query(Dbentity).filter(Dbentity.display_name.like('saccharomyces_cerevisiae.%.gff.gz')).filter(
        Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    nex_session.commit()

    data_id = edam_to_id.get('EDAM:3671')  # data:3671    Text
    # topic:3068   Literature and language
    topic_id = edam_to_id.get('EDAM:3068')
    format_id = edam_to_id.get('EDAM:3507')  # format:3507  Document format

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    readme = nex_session.query(Dbentity).filter_by(
        display_name="saccharomyces_cerevisiae_gff.README", dbentity_status='Active').one_or_none()
    if readme is None:
        log.info("saccharomyces_cerevisiae_gff.README is not in the database.")
        return
    readme_file_id = readme.dbentity_id

    # path.path = /reports/chromosomal-features

    upload_file(CREATED_BY, local_file,
                filename=gzip_file,
                file_extension='gz',
                description='GFF file for yeast genes (protein and RNA)',
                display_name=gzip_file,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                readme_file_id=readme_file_id,
                is_public=True,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_to_id['SGD'],
                md5sum=gff_md5sum)

    gff = nex_session.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()

    if gff is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = gff.dbentity_id
    sgdid = gff.sgdid
    log.info("The file will be uploaded to s3://sgd-[dev|prod]-upload/" + sgdid + "/" + gzip_file)
    
    path = nex_session.query(Path).filter_by(
        path="/reports/chromosomal-features").one_or_none()
    if path is None:
        log.info("The path: /reports/chromosomal-features is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_to_id['SGD'],
                 created_by=CREATED_BY)

    nex_session.add(x)
    nex_session.commit()

    log.info("Done uploading " + gff_file)


def write_header(fw, datestamp):

    fw.write("##gff-version 3\n")
    fw.write("#!date-produced " + datestamp.split(".")[0] + "\n")
    fw.write("#!data-source SGD\n")
    fw.write("#!assembly R64-4-1\n")
    fw.write("#!refseq-version GCF_000146045.2\n")
    fw.write("#\n")
    fw.write("# Saccharomyces cerevisiae S288C genome (version=R64-4-1)\n")
    fw.write("#\n")
    fw.write("# Features from the 16 nuclear chromosomes labeled chrI to chrXVI,\n")
    fw.write("# plus the mitochondrial genome labeled chrmt.\n")
    fw.write("#\n")
    fw.write(
        "# Created by Saccharomyces Genome Database (http://www.yeastgenome.org/)\n")
    fw.write("#\n")
    fw.write("# Weekly updates of this file are available for download from:\n")
    fw.write(
        "# https://downloads.yeastgenome.org/latest/saccharomyces_cerevisiae.gff.gz\n")
    fw.write("#\n")
    fw.write(
        "# Please send comments and suggestions to sgd-helpdesk@lists.stanford.edu\n")
    fw.write("#\n")
    fw.write("# SGD is funded as a National Human Genome Research Institute Biomedical Informatics Resource from\n")
    fw.write("# the U. S. National Institutes of Health to Stanford University.\n")
    fw.write("#\n")


if __name__ == '__main__':

    dump_data()
