from src.helpers import upload_file
from src.boto3_upload import upload_one_file_to_s3
from scripts.loading.database_session import get_session
from src.models import Dbentity, Filedbentity, Referencedbentity, Edam,\
    FilePath, Path, ReferenceFile, Source
from datetime import datetime
import logging
import os
import hashlib

__author__ = 'sweng66'

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

supplFileDir = "scripts/loading/suppl_files/pubmed_pmc_download/"


def load_data():
    """Load PMC file metadata into the database.

    Handles new directory structure: pubmed_pmc_download/{PMID}/{PMCID}/{files}
    """
    nex_session = get_session()

    log.info(datetime.now())
    log.info("Getting data from database...")

    edam_to_id = dict([(x.format_name, x.edam_id) for x in nex_session.query(Edam).all()])
    src = nex_session.query(Source).filter_by(display_name='SGD').one_or_none()
    source_id = src.source_id
    pmid_to_reference_id_year = dict([
        (x.pmid, (x.dbentity_id, x.year))
        for x in nex_session.query(Referencedbentity).filter(Referencedbentity.pmid.isnot(None)).all()
    ])

    # Track files already in database by (reference_id, previous_file_name)
    existing_files = set()
    for x in nex_session.query(Filedbentity).filter_by(description='PubMed Central download').all():
        existing_files.add(x.previous_file_name)

    log.info(datetime.now())
    log.info("Loading file metadata into database...")

    file_count = 0
    skip_count = 0
    error_count = 0

    # Iterate through PMID directories
    if not os.path.exists(supplFileDir):
        log.info(f"Directory not found: {supplFileDir}")
        return

    for pmid_dir in os.listdir(supplFileDir):
        pmid_path = os.path.join(supplFileDir, pmid_dir)

        if not os.path.isdir(pmid_path):
            continue

        try:
            pmid = int(pmid_dir)
        except ValueError:
            log.warning(f"Skipping non-PMID directory: {pmid_dir}")
            continue

        if pmid not in pmid_to_reference_id_year:
            log.info(f"PMID:{pmid} is not in the database.")
            continue

        (reference_id, year) = pmid_to_reference_id_year[pmid]

        # Iterate through PMCID subdirectories
        for pmcid_dir in os.listdir(pmid_path):
            pmcid_path = os.path.join(pmid_path, pmcid_dir)

            if not os.path.isdir(pmcid_path):
                continue

            # Iterate through files in PMCID directory
            for filename in os.listdir(pmcid_path):
                file_path = os.path.join(pmcid_path, filename)

                if not os.path.isfile(file_path):
                    continue

                # Use a unique identifier for the file
                unique_filename = f"{pmid}_{pmcid_dir}_{filename}"

                if unique_filename in existing_files:
                    skip_count += 1
                    continue

                try:
                    update_database_load_file_to_s3(
                        nex_session, file_count + 1, file_path, filename,
                        unique_filename, source_id, edam_to_id, year, reference_id
                    )
                    existing_files.add(unique_filename)
                    file_count += 1
                except Exception as e:
                    error_count += 1
                    log.error(f"Error loading {file_path}: {e}")

    nex_session.close()

    log.info(datetime.now())
    log.info(f"Done! Loaded {file_count} files, skipped {skip_count}, errors {error_count}")


def update_database_load_file_to_s3(nex_session, count, file_path, display_filename,
                                     unique_filename, source_id, edam_to_id, year, reference_id):
    """Load a single file's metadata into the database."""

    local_file = open(file_path, mode='rb')

    # Calculate md5sum of file content
    md5sum = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5sum.update(chunk)
    md5sum = md5sum.hexdigest()

    row = nex_session.query(Filedbentity).filter_by(md5sum=md5sum).one_or_none()
    if row is not None:
        return

    row = nex_session.query(Dbentity).filter(Dbentity.display_name == unique_filename).all()
    if len(row) > 0:
        return

    data_id = edam_to_id.get('EDAM:2526')
    topic_id = edam_to_id.get('EDAM:3070')
    format_id = edam_to_id.get('EDAM:2330')

    from sqlalchemy import create_engine
    from src.models import DBSession
    engine = create_engine(os.environ['NEX2_URI'], pool_recycle=3600)
    DBSession.configure(bind=engine)

    # Determine file extension
    if display_filename.endswith('.gz'):
        file_extension = 'gz'
    else:
        parts = display_filename.rsplit('.', 1)
        file_extension = parts[1] if len(parts) > 1 else ''

    upload_file(CREATED_BY, local_file,
                filename=unique_filename,
                file_extension=file_extension,
                description='PubMed Central download',
                display_name=unique_filename,
                year=year,
                data_id=data_id,
                format_id=format_id,
                topic_id=topic_id,
                status='Active',
                is_public=True,
                is_in_spell=False,
                is_in_browser=False,
                file_date=datetime.now(),
                source_id=source_id,
                md5sum=md5sum)

    row = nex_session.query(Dbentity).filter_by(
        display_name=unique_filename, dbentity_status='Active'
    ).one_or_none()
    if row is None:
        log.info("The " + unique_filename + " is not in the database.")
        return
    file_id = row.dbentity_id

    path = nex_session.query(Path).filter_by(path="/supplemental_data").one_or_none()
    if path is None:
        log.info("The path /supplemental_data is not in the database.")
        return
    path_id = path.path_id

    x = FilePath(file_id=file_id,
                 path_id=path_id,
                 source_id=source_id,
                 created_by=CREATED_BY)

    nex_session.add(x)

    x = ReferenceFile(file_id=file_id,
                      reference_id=reference_id,
                      file_type='Supplemental',
                      source_id=source_id,
                      created_by=CREATED_BY)
    nex_session.add(x)

    nex_session.commit()

    log.info(str(count) + " done loading " + unique_filename)


if __name__ == '__main__':

    load_data()
