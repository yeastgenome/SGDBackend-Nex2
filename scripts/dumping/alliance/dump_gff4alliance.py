import logging
import os
import sys
import shutil
import gzip
import importlib
importlib.reload(sys)  # Reload does the trick!

from datetime import datetime
from sqlalchemy import create_engine
from src.models import Dbentity, DBSession, Locusdbentity, LocusAlias, Dnasequenceannotation, \
    Dnasubsequence, So, Contig, Go, Goannotation, Edam, Path, \
    FilePath, Filedbentity, Source, Transcriptdbentity

engine = create_engine(os.getenv('NEX2_URI'), pool_recycle=3600, pool_size=100)
DBSession.configure(bind=engine)

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

gff_file = "/Users/kkarra/Dev/SGDBackend-Nex2/scripts/dumping/alliance/data/saccharomyces_cerevisiae_forAlliance.gff"
landmark_file = "/Users/kkarra/Dev/SGDBackend-Nex2/scripts/dumping/alliance/data/landmark_gene.txt"

chromosomes = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX',
               'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'Mito']

## If transcript < gene start/stop then add start/stop as transcript and SKIP transcript in the database;
# workaround until transcripts fixed after updates ##

def dump_data():

    fw = open(gff_file, "w")
    datestamp = str(datetime.now()).split(" ")[0].replace("-", "")
    write_header(fw, datetime.utcnow().strftime("%Y-%m-%dT%H:%m:%S-00:00"))
    log.info(str(datetime.now()))

    log.info("Getting edam, so, uniprot, source, & sgdid data from the database...")

    locus_id_to_uniprot = dict([(x.locus_id, x.display_name) for x in DBSession.query(
        LocusAlias).filter_by(alias_type='UniProtKB ID').all()])

    locus_id_to_refseq = dict([(x.locus_id, x.display_name) for x in DBSession.query(
        LocusAlias).filter_by(alias_type='RefSeq nucleotide version ID').all()])

    log.info("num uniprot ids:" + str(len(locus_id_to_uniprot.keys())))
    log.info("num refseq ids:" + str(len(locus_id_to_refseq.keys())))

    edam_to_id = dict([(x.format_name, x.edam_id)
                       for x in DBSession.query(Edam).all()])

    log.info("num edam objs:" + str(len(edam_to_id.keys())))
    source_to_id = dict([(x.display_name, x.source_id)
                         for x in DBSession.query(Source).all()])
    so_id_to_term_name = dict([(x.so_id, x.term_name)
                               for x in DBSession.query(So).all()])
    so = DBSession.query(So).filter_by(display_name='gene').one_or_none()
    gene_soid = so.soid
    locus_id_to_sgdid = dict([(x.dbentity_id, x.sgdid) for x in DBSession.query(
        Dbentity).filter_by(subclass='LOCUS', dbentity_status='Active').all()])

    log.info("locus to sgdid:" + str(len(locus_id_to_sgdid.keys())))

    log.info(str(datetime.now()))
    log.info("Getting alias data from the database...")

    alias_data = DBSession.query(LocusAlias).filter(LocusAlias.alias_type.in_(
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
                             for x in DBSession.query(Locusdbentity).filter_by(has_summary='1').all()])

    log.info(str(datetime.now()))
    log.info("Getting go annotation data from the database...")

    go_id_to_goid = dict([(x.go_id, x.goid)
                          for x in DBSession.query(Go).all()])

    go_data = DBSession.query(Goannotation).filter(
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
        x.residues))) for x in DBSession.query(Contig).filter(Contig.format_name.in_(format_name_list)).all()])
    chr_to_seq = dict([(x.format_name.replace("Chromosome_", ""), x.residues) for x in DBSession.query(
        Contig).filter(Contig.format_name.in_(format_name_list)).all()])

    log.info(str(datetime.now()))
    log.info("Getting dnasequenceannotation/dnasubsequence data from the database...")

    subfeature_data = DBSession.query(Dnasubsequence).order_by(
        Dnasubsequence.contig_start_index, Dnasubsequence.contig_end_index).all()

    landmark_gene = get_landmark_genes()

    log.info(str(datetime.now()))
    log.info("Getting transcript data from the database...")

    ## get transcript data in database ##
    systematic_name_to_transcripts = {}
    transcript_range = {}

    transcripts = DBSession.query(
        Dbentity).filter_by(subclass='TRANSCRIPT').all()
    log.info("num of transcript objs: " + str(len(transcripts)))

    # make dict of transcripts to systematic name; ONLY ADD Pelechano transcript is as long as or longer than geneomic start/stop
    for transcriptObj in transcripts:
        transSeqAnnot = DBSession.query(Dnasequenceannotation).filter_by(
            dbentity_id=transcriptObj.dbentity_id).first()
        sysName = transcriptObj.format_name.split("_")[0]
        #log.info(sysName + " has transcript " + transcriptObj.display_name)

        transcriptConds = DBSession.query(Transcriptdbentity).filter_by(
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

        if sysName in transcript_range:
            (start, stop) = transcript_range[sysName]
            if transSeqAnnot.start_index < start or transSeqAnnot.end_index > stop:
                transcript_range[sysName] = (transSeqAnnot.start_index, transSeqAnnot.end_index)
        else:
            transcript_range[sysName] = (transSeqAnnot.start_index, transSeqAnnot.end_index)

        if sysName in systematic_name_to_transcripts.keys():
            systematic_name_to_transcripts[sysName].append({"sgdid": "SGD:" + transcriptObj.sgdid,
                                                            "name": transcriptObj.format_name,
                                                            "start": transSeqAnnot.start_index,
                                                            "end": transSeqAnnot.end_index,
                                                            "contig": transSeqAnnot.contig,
                                                            "strand": transSeqAnnot.strand,
                                                            "conditions": ",".join(tconditions)})
        else:
            systematic_name_to_transcripts[sysName] = [{"sgdid": "SGD:" + transcriptObj.sgdid,
                                                        "name": transcriptObj.format_name,
                                                        "start": transSeqAnnot.start_index,
                                                        "end": transSeqAnnot.end_index,
                                                        "contig": transSeqAnnot.contig,
                                                        "strand": transSeqAnnot.strand,
                                                        "conditions": ",".join(tconditions)}]

    for chr in chromosomes:

        (contig_id, accession_id, length) = chr_to_contig[chr]

        if chr == 'Mito':
            chr = 'mt'
        log.info(chr + " features")

        fw.write("chr" + chr + "\tSGD\tchromosome\t1\t" + str(length) + "\t.\t.\t.\tID=chr" +
                 chr + ";dbxref=NCBI:" + accession_id + ";Name=chr" + chr + "\n")

        # get features for each contig_id
        # print features in the order of chromosome and coord

        gene_data = DBSession.query(Dnasequenceannotation).filter_by(contig_id=contig_id, dna_type='GENOMIC').order_by(
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

            type = so_id_to_term_name[x.so_id]
            if type == 'ORF':
                type = 'gene'
            if type == 'gene_group':
                continue

            (systematic_name, gene_name, qualifier, headline,
             description) = locus_id_to_info[x.dbentity_id]

            if systematic_name in landmark_gene:
                fw.write("chr" + chr + "\tlandmark\tregion\t" + str(x.start_index) + "\t" + str(
                    x.end_index) + "\t.\t" + x.strand + "\t.\tID=" + landmark_gene[systematic_name] + "\n")

            systematic_name = do_escape(systematic_name)
            alias_list = None
            if x.dbentity_id in locus_id_to_aliases:
                aliases = sorted(locus_id_to_aliases[x.dbentity_id])
                alias_list = ",".join(aliases)
            if gene_name:
                gene_name = do_escape(gene_name)
                name_attribute = gene_name
                if alias_list:
                    alias_list = gene_name + "," + systematic_name + "," + alias_list
                else:
                    alias_list = gene_name
            else:
                name_attribute = systematic_name
            strand = x.strand
            if strand == '0':
                strand = '.'
            start_index = x.start_index
            end_index = x.end_index
            if x.annotation_id in UTRs:
                (utrStart, utrEnd) = UTRs[x.annotation_id]
                if utrStart < start_index:
                    start_index = utrStart
                else:
                    end_index = utrEnd
## This is where you'd check to put something if you were to NOT write IF type is CDS AND there are Pelechano transcripts ??##
            gene_start = start_index
            gene_end = end_index

            if systematic_name in transcript_range:
                (transcript_start, transcript_stop) = transcript_range[systematic_name]
                if transcript_start < gene_start:
                    gene_start = transcript_start
                if transcript_stop > gene_end:
                    gene_end = transcript_stop
            if type == "gene":
                fw.write("chr" + chr + "\tSGD\t" + type + "\t" + str(gene_start) + "\t" + str(gene_end) +
                         "\t.\t" + strand + "\t.\tID=" + systematic_name + ";Name=" + name_attribute)
            else:
                fw.write("chr" + chr + "\tSGD\t" + type + "\t" + str(start_index) + "\t" + str(end_index) +
                     "\t.\t" + strand + "\t.\tID=" + systematic_name + ";Name=" + name_attribute)

            if gene_name:
                fw.write(";gene=" + gene_name)
            if alias_list:
                fw.write(";Alias=" + alias_list)
            if x.dbentity_id in locus_id_to_goids:
                goids = sorted(locus_id_to_goids[x.dbentity_id])
                goid_list = ",".join(goids)
                fw.write(";Ontology_term=" + goid_list + "," + gene_soid)
            if description:
                fw.write(";Note=" + do_escape(description))
            if headline:
                fw.write(";display=" + do_escape(headline))

            fw.write(";dbxref=" + sgdid)

            # if "gene" in type:
            #    fw.write(";gene_id=" + sgdid)

            if qualifier:
                fw.write(";orf_classification=" + qualifier)

 # FOR Alliance GFF3; 

            if "gene" in type:
                fw.write(";gene_id=" + sgdid)

            fw.write(";curie=" + sgdid + "\n")

            ## add UniProt ID for CDs ##
 #               # fw.write(";protein_id=" + uniprotid)
 #           elif "CDS" in type and uniprotid in locals():
#                fw.write(";protein_id=" + uniprotid +
 #                        ";curie=" + uniprotid + "\n")

 #           elif "mRNA" in type and refseqid in locals():
 #               fw.write(";transcript_id=" + refseqid +
 #                        ";curie=" + refseqid + "\n")

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
                            #  log.info(systematic_name +
                            #           " CDS parent: " + parent)
                        parent = ",".join(parentList)
                    else:
                        parent = systematic_name + "_mRNA"
                elif type.endswith('_gene'):
                    rnaType = type.replace("_gene", "")
                    parent = systematic_name + "_" + rnaType

                has_subfeature = 1

                fw.write("chr" + chr + "\tSGD\t" + display_name + "\t" + str(contig_start_index) + "\t" + str(
                    contig_end_index) + "\t.\t" + x.strand + "\t" + str(phase) + "\tParent=" + parent + ";Name=" + name)
                if type == 'gene' and qualifier:
                    fw.write(";orf_classification=" + qualifier)
                # FOR Alliance ##
                if display_name == 'CDS' and uniprotid != "":
                    fw.write(";curie=" + uniprotid +
                             ";protein_id=" + uniprotid + "\n")
                    # write exon row for Alliance #
                    fw.write("chr" + chr + "\tSGD\texon\t" + str(contig_start_index) + "\t" + str(
                        contig_end_index) + "\t.\t" + x.strand + "\t" + str(phase) + "\tParent=" + parent)

                fw.write("\n")

                # fw.write("chr" + chr + "\tSGD\t" + display_name + "\t" + str(contig_start_index) + "\t" + str(contig_end_index) + "\t.\t" + strand + "\t" + str(phase) + "\tID=" + name + ";Name=" + name + ";dbxref=" + sgdid + ";curie=" + sgdid + "\n");

            if type == 'gene':
                if systematic_name in systematic_name_to_transcripts.keys(): #add exprimental transcripts #
                    for each in systematic_name_to_transcripts[systematic_name]:
                        if refseqid != "":
                            fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(each["start"]) + "\t" + str(each["end"]) + "\t.\t" + each["strand"] + "\t.\tID=" + each["name"] +
                                     ";Name=" + each["name"] + ";Parent=" + systematic_name + ";transcript_id=" + each["sgdid"] + ";curie=" + each["sgdid"] + ";dbxref=" + refseqid+";conditions=" + each["conditions"]+"\n")
                        else:
                            fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(each["start"]) + "\t" + str(each["end"]) + "\t.\t" + each["strand"] +
                                     "\t.\tID=" + each["name"] + ";Name=" + each["name"] + ";Parent=" + systematic_name + ";transcript_id=" + each["sgdid"] + ";curie=" + each["sgdid"] + ";conditions=" + each["conditions"] + "\n")
                else:  # no experimental transcripts #
                    if refseqid != "":
                        fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(start_index) + "\t" + str(end_index) + "\t.\t" + x.strand + "\t.\tID=" + systematic_name +
                                 "_mRNA;Name=" + systematic_name + "_mRNA;Parent=" + systematic_name + ";transcript_id="+refseqid + ";curie=" + refseqid+"\n")
                    else:
                        fw.write("chr" + chr + "\tSGD\tmRNA\t" + str(start_index) + "\t" + str(end_index) + "\t.\t" + x.strand +
                                 "\t.\tID=" + systematic_name + "_mRNA;Name=" + systematic_name + "_mRNA;Parent=" + systematic_name + "\n")
            elif has_subfeature == 1:
                rnaType = type.replace("_gene", "")
                fw.write("chr" + chr + "\tSGD\t" + rnaType + "\t" + str(start_index) + "\t" + str(end_index) + "\t.\t" + x.strand + "\t.\tID=" +
                         systematic_name + "_" + rnaType + ";Name=" + systematic_name + "_" + rnaType + ";Parent=" + systematic_name + "\n")

    # output 17 chr sequences at the end
# COMMENTED OUT FOR ALLIANCE #
 #   fw.write("###\n")
 #   fw.write("##FASTA\n")

 #   for chr in chromosomes:
 #       seq = chr_to_seq[chr]
 #       if chr == 'Mito':
 #           chr = 'mt'
 #       fw.write(">chr" + chr + "\n")
 #       formattedSeq = formated_seq(seq)
 #       fw.write(formattedSeq + "\n")

    fw.close()
    gzip_file = gzip_gff_file(gff_file, datestamp)

    # log.info("Uploading gff3 file to S3...")
    # update_database_load_file_to_s3(nex_session, gff_file, gzip_file, source_to_id, edam_to_id)

    DBSession.close()
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
    text = text.rstrip()
    return text


#def upload_gff_to_s3(file, filename):

#    s3_path = filename
#    conn = boto.connect_s3(S3_ACCESS_KEY, S3_SECRET_KEY)
#    bucket = conn.get_bucket(S3_BUCKET)
#    k = Key(bucket)
#    k.key = s3_path
#    k.set_contents_from_file(file, rewind=True)
##    k.make_public()
#    transaction.commit()


def gzip_gff_file(gff_file, datestamp):

    # gff_file  = saccharomyces_cerevisiae.gff
    # gzip_file = saccharomyces_cerevisiae.20170114.gff.gz
    gzip_file = gff_file.replace(".gff", "") + "." + datestamp + ".gff.gz"

    with open(gff_file, 'rb') as f_in, gzip.open(gzip_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    return gzip_file


def update_database_load_file_to_s3(DBSession, gff_file, gzip_file, source_to_id, edam_to_id):

    local_file = open(gzip_file, mode='rb')

    ### upload a current GFF file to S3 with a static URL for Go Community ###
  #  upload_gff_to_s3(local_file, "latest/saccharomyces_cerevisiae.gff.gz")
    ##########################################################################

    import hashlib
    gff_md5sum = hashlib.md5(gzip_file.encode()).hexdigest()
    row = DBSession.query(Filedbentity).filter_by(
        md5sum=gff_md5sum).one_or_none()

    if row is not None:
        return

    gzip_file = gzip_file.replace("scripts/dumping/curation/data/", "")

    DBSession.query(Dbentity).filter(Dbentity.display_name.like('saccharomyces_cerevisiae.%.gff.gz')).filter(
        Dbentity.dbentity_status == 'Active').update({"dbentity_status": 'Archived'}, synchronize_session='fetch')
    DBSession.commit()

    data_id = edam_to_id.get('EDAM:3671')  # data:3671    Text
    # topic:3068   Literature and language
    topic_id = edam_to_id.get('EDAM:3068')
    format_id = edam_to_id.get('EDAM:3507')  # format:3507  Document format

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    readme = DBSession.query(Dbentity).filter_by(
        display_name="saccharomyces_cerevisiae_gff.README", dbentity_status='Active').one_or_none()
    if readme is None:
        log.info("saccharomyces_cerevisiae_gff.README is not in the database.")
        return
    readme_file_id = readme.dbentity_id

    # path.path = /reports/chromosomal-features

   # upload_file(CREATED_BY, local_file,
   #             filename=gzip_file,
   #             file_extension='gz',
   #             description='GFF file for yeast genes (protein and RNA)',
   #             display_name=gzip_file,
   #             data_id=data_id,
   #             format_id=format_id,
   #             topic_id=topic_id,
   #             status='Active',
   #             readme_file_id=readme_file_id,
   #             is_public='1',
   #             is_in_spell='0',
   #             is_in_browser='0',
   #             file_date=datetime.now(),
   # source_id=source_to_id['SGD'],
   #             md5sum=gff_md5sum)

    gff = DBSession.query(Dbentity).filter_by(
        display_name=gzip_file, dbentity_status='Active').one_or_none()

    if gff is None:
        log.info("The " + gzip_file + " is not in the database.")
        return
    file_id = gff.dbentity_id

    path = DBSession.query(Path).filter_by(
        path="/reports/chromosomal-features").one_or_none()
    if path is None:
        log.info("The path: /reports/chromosomal-features is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_to_id['SGD'],
                 created_by=CREATED_BY)

    DBSession.add(x)
    DBSession.commit()

    log.info("Done uploading " + gff_file)


def write_header(fw, datestamp):

    fw.write("##gff-version 3\n")
    fw.write("#!date-produced " + datestamp+"\n") #.split(".")[0] + "\n")
    fw.write("#!data-source SGD\n")
    fw.write("#!assembly R64-3-1\n")
    fw.write("#!refseq-version GCF_000146045.2\n")
    fw.write("#\n")
    fw.write("# Saccharomyces cerevisiae S288C genome (version=R64-3-1)\n")
    fw.write("#\n")
    fw.write("# Features from the 16 nuclear chromosomes labeled chrI to chrXVI,\n")
    fw.write("# plus the mitochondrial genome labeled chrmt.\n")
    fw.write("#\n")
    fw.write("# Created by Saccharomyces Genome Database (http://www.yeastgenome.org/) for Alliance project.\n")
    fw.write("#\n")
    fw.write("# SGD versions of this file are available for download from:\n")
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
