import json
from urllib.request import Request, urlopen
from urllib.error import URLError
import logging
import os
from datetime import datetime
import sys
import importlib
importlib.reload(sys)  # Reload does the trick!
from src.models import Psimi, Taxonomy, Dbentity, Complexbindingannotation, Interactor
from scripts.loading.database_session import get_session
from scripts.loading.reference.promote_reference_triage import add_paper

__author__ = 'sweng66'

## Created on March 2018
## This script is used to load IntAct protein complex data into NEX2

TAXON_ID = "TAX:559292"

logging.basicConfig(format='%(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

CREATED_BY = os.environ['DEFAULT_USER']

detail_json_url_template = "https://www.ebi.ac.uk/intact/complex-ws/complex/REPLACE_ID_HERE"

log_file = "scripts/loading/complex/logs/load_complexbindingannotation.log"


def load_complexbindingannotation():

    nex_session = get_session()

    format_name_to_psimi_id = dict([(x.format_name, x.psimi_id) for x in nex_session.query(Psimi).all()])
    taxon = nex_session.query(Taxonomy).filter_by(taxid=TAXON_ID).one_or_none()
    taxonomy_id = taxon.taxonomy_id

    complexAC_to_dbentity = dict([(x.format_name, x) for x in nex_session.query(Dbentity).filter_by(subclass='COMPLEX').all()])
    interactor_to_id = dict([(x.format_name, x.interactor_id) for x in nex_session.query(Interactor).all()])
 
    fw = open(log_file, "w")

    key_to_annotation = {}
    for x in nex_session.query(Complexbindingannotation).all():
        binding_interactor_id = x.binding_interactor_id
        if binding_interactor_id is None:
            binding_interactor_id = -1
        # range_start/range_end are part of the key: a subunit pair can have
        # several distinct binding regions that differ only by range (e.g. the
        # three Mg2+ binding sites on ILV2 in CPX-3034).
        key = (x.complex_id, x.interactor_id, binding_interactor_id, x.range_start, x.range_end)
        key_to_annotation[key] = (x.binding_type_id, x.range_start, x.range_end, x.stoichiometry, x.binding_region_name)

    loaded = {}

    for complexAC in complexAC_to_dbentity:


        print("Getting info for ", complexAC)


        d =  complexAC_to_dbentity[complexAC]
        source_id = d.source_id
        complex_id = d.dbentity_id
        
        detailUrl = detail_json_url_template.replace("REPLACE_ID_HERE", complexAC)
        
        y = get_json(detailUrl)
        if y == 404:
            print("Can't access:", detailUrl)
            continue

        for p in y['participants']:

            interactor = p['identifier']
            interactor_id = interactor_to_id.get(interactor)
            if interactor_id is None:
                print("The interactor: ", interactor, " is not in the database.")
                continue
                
            stoichiometry = p.get('stochiometry')
            if stoichiometry is not None and stoichiometry == 'null':
                stoichiometry = None
            elif stoichiometry is not None and "maxValue" in stoichiometry:
                stoichiometry = int(stoichiometry.split("maxValue: ")[1])

            bindingInteractors = []

            linkedFeatures = p.get('linkedFeatures')
            if linkedFeatures is None or len(linkedFeatures) == 0:
                # no binding interactor
                bindingInteractors.append((-1, None, None, None, None))
            else:
                for lf in linkedFeatures:
                    binding_interactor = lf.get('participantId')
                    if binding_interactor is None:
                        continue
                    binding_interactor_id = interactor_to_id.get(binding_interactor)
                    if binding_interactor_id is None:
                        print("The binding interactor: ", binding_interactor, " is not in the database.")
                        continue
                    binding_type = lf.get('featureTypeMI')
                    if binding_type is None:
                        print("No binding type for ", complexAC, interactor, binding_interactor)
                        continue
                    binding_type_id = format_name_to_psimi_id.get(binding_type)
                    if binding_type_id is None:
                        print("The binding_type:", binding_type, " is not in the PSIMI table.")
                        continue

                    # Human-readable label of the binding region, e.g.
                    # "mg2+ binding site (asn-577)".
                    binding_region_name = lf.get('name')

                    ranges = lf.get('ranges')

                    (range_start, range_end) = cleanup_ranges(ranges)

                    print("ranges:", ranges, range_start, range_end)

                    bindingInteractors.append((binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name))

            for b in bindingInteractors:

                (binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name) = b

                key = (complex_id, interactor_id, binding_interactor_id, range_start, range_end)

                if key in loaded:
                    continue

                loaded[key] = 1

                annotation_in_db = key_to_annotation.get(key)

                if annotation_in_db is None:

                    insert_annotation(nex_session, fw, complex_id, interactor_id, binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name, stoichiometry, source_id, taxonomy_id)
                    continue

                update_annotation(nex_session, fw, complex_id, interactor_id, binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name, stoichiometry, annotation_in_db, source_id, taxonomy_id)

        # nex_session.rollback()
        nex_session.commit()  

    for key in key_to_annotation:
        if key not in loaded:
            (complex_id, interactor_id, binding_interactor_id, range_start, range_end) = key
            if binding_interactor_id == -1:
                nex_session.query(Complexbindingannotation).filter_by(complex_id=complex_id, interactor_id=interactor_id, range_start=range_start, range_end=range_end).delete()
                fw.write("The Complexbindingannotation for complex_id=" + str(complex_id) + ", interactor_id=" + str(interactor_id) + ", binding_interactor_id=None, range_start=" + str(range_start) + ", range_end=" + str(range_end) + " has been deleted.\n")
            else:
                nex_session.query(Complexbindingannotation).filter_by(complex_id=complex_id, interactor_id=interactor_id, binding_interactor_id=binding_interactor_id, range_start=range_start, range_end=range_end).delete()
                fw.write("The Complexbindingannotation for complex_id=" + str(complex_id) + ", interactor_id=" + str(interactor_id) + ", binding_interactor_id=" + str(binding_interactor_id) + ", range_start=" + str(range_start) + ", range_end=" + str(range_end) + " has been deleted.\n")

    # nex_session.rollback()
    nex_session.commit()  

 
def insert_annotation(nex_session, fw, complex_id, interactor_id, binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name, stoichiometry, source_id, taxonomy_id):

    if binding_interactor_id == -1:
        binding_interactor_id = None

    x = Complexbindingannotation(complex_id = complex_id,
                                 interactor_id = interactor_id,
                                 binding_interactor_id = binding_interactor_id,
                                 binding_type_id = binding_type_id,
                                 source_id = source_id,
                                 taxonomy_id = taxonomy_id,
                                 reference_id = None,
                                 range_start = range_start,
                                 range_end = range_end,
                                 binding_region_name = binding_region_name,
                                 stoichiometry = stoichiometry,
                                 created_by = CREATED_BY)
    nex_session.add(x)

    fw.write("Add a new Complexbindingannotation row for complex_id=" + str(complex_id) + ", interactor_id=" + str(interactor_id) + ", binding_interactor_id="+ str(binding_interactor_id) + ", range_start=" + str(range_start) + ", range_end=" + str(range_end) + "\n")
    

def update_annotation(nex_session, fw, complex_id, interactor_id, binding_interactor_id, binding_type_id, range_start, range_end, binding_region_name, stoichiometry, annotation_in_db, source_id, taxonomy_id):

    (binding_type_id_db, range_start_db, range_end_db, stoichiometry_db, binding_region_name_db) = annotation_in_db

    update_hash = {}
    if binding_type_id != binding_type_id_db:
        update_hash['binding_type_id'] = binding_type_id
    if range_start != range_start_db:
        update_hash['range_start'] = range_start
    if range_end != range_end_db:
        update_hash['range_end'] = range_end
    if binding_region_name != binding_region_name_db:
        update_hash['binding_region_name'] = binding_region_name
    if stoichiometry and stoichiometry != stoichiometry_db:
        update_hash['stoichiometry'] = stoichiometry

    if not update_hash:
        return

    # range_start/range_end are part of the row identity now, so they must be in
    # the WHERE clause -- otherwise the update would hit every binding region for
    # this subunit pair.
    if binding_interactor_id == -1:
        nex_session.query(Complexbindingannotation).filter_by(complex_id=complex_id, interactor_id=interactor_id, range_start=range_start, range_end=range_end).update(update_hash)
        fw.write("The Complexbindingannotation for complex_id=" + str(complex_id) + ", interactor_id=" + str(interactor_id) + ", binding_interactor_id=None, range_start=" + str(range_start) + ", range_end=" + str(range_end) + " has been updated.\n")
    else:
        nex_session.query(Complexbindingannotation).filter_by(complex_id=complex_id, interactor_id=interactor_id, binding_interactor_id=binding_interactor_id, range_start=range_start, range_end=range_end).update(update_hash)
        fw.write("The Complexbindingannotation for complex_id=" + str(complex_id) + ", interactor_id=" + str(interactor_id) + ", binding_interactor_id=" + str(binding_interactor_id) + ", range_start=" + str(range_start) + ", range_end=" + str(range_end) + " has been updated.\n")
   

def cleanup_ranges(ranges):

    range_start = None
    range_end = None
    if ranges[0] != '?-?':
        ranges[0] = ranges[0].replace(">", "").replace("<", "")
        range_start = ranges[0].split("-")[0].split("..")[0]
        range_end = ranges[0].split("-")[1].split("..")[0]

        if range_start is not None and range_start in ['n', 'c', '?']:
            range_start = None
        if range_end is not None and range_end in ['n', 'c', '?']:
            range_end = None

    # Return ints so keys built from the JSON match the integer values read back
    # from the database on subsequent runs.
    return (to_int(range_start), to_int(range_end))


def to_int(value):

    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_json(url):

    print("get json:", url)

    try:
        req = Request(url)
        res = urlopen(req)
        raw_data = res.read().decode('utf-8', "ignore")
        data = json.loads(raw_data)
        return data
    except URLError:
        return 404

def fix_a_few_interactors():

    subunit2orfMapping = {
        "rnk_yeast":   "YPR170W-B", 
        "yhs2_yeast":  "YHR122W",   
        "yg29_yeast":  "YGR066C",
        "yl149_yeast": "YLR149C"
    }
    nex_session = get_session()
    for subunit in subunit2orfMapping:
        orf = subunit2orfMapping[subunit]
        x = nex_session.query(Dbentity).filter_by(format_name=orf).one_or_none()
        if x:
            y = nex_session.query(Interactor).filter_by(display_name=subunit).one_or_none()
            if y and y.locus_id != x.dbentity_id:
                y.locus_id = x.dbentity_id
                nex_session.commit()
                print("Fixing locus_id for " + subunit)
    nex_session.close()


if __name__ == "__main__":

    load_complexbindingannotation()
    fix_a_few_interactors()
