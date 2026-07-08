from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from src.models import DBSession, Dbentity, CurationReference, Literatureannotation, \
                       Locusdbentity, Referencedbentity, Pathwaydbentity, Source, Taxonomy
from src.curation_helpers import get_curator_session

TAXON = 'TAX:4932'

def group_papers(curationObjs):

    ids_to_annotation = dict([((x.reference_id, x.dbentity_id), (x.annotation_id, x.topic)) for x in DBSession.query(Literatureannotation).all()])

    key2paper = {}
    key2genelist = {}
    for x in curationObjs:
        topic = None
        annotation_id = None
        if x.dbentity_id and (x.reference_id, x.dbentity_id) in ids_to_annotation: 
            (annotation_id, topic) = ids_to_annotation[(x.reference_id, x.dbentity_id)]
        key = (x.reference_id, x.curation_tag, topic) 
        refObj = x.reference
        dbentity = x.dbentity
        key2paper[key] = (refObj.citation, refObj.pmid, refObj.year, x.date_created, x.curator_comment)
        
        if dbentity is not None:
            name = dbentity.display_name
            if dbentity.subclass == 'COMPLEX':
                name = dbentity.format_name
            elif dbentity.subclass == 'PATHWAY':
                pathway = DBSession.query(Pathwaydbentity).filter_by(dbentity_id=dbentity.dbentity_id).one_or_none()
                name = pathway.biocyc_id
            elif dbentity.subclass == 'ALLELE':
                name = dbentity.display_name
                
            name = name + '|' + str(x.curation_id) + '|' + str(annotation_id)

            genelist = []
            if key in key2genelist:
                genelist = key2genelist[key]
            genelist.append(name)
            key2genelist[key] = genelist
            
    data = []
    for key in key2paper:
        (reference_id, tag, topic) = key
        (citation, pmid, year, date_created, comment) = key2paper[key]
        gene_list = []
        if key in key2genelist:
            gene_list = sorted(key2genelist[key])
        row = { "citation": citation,
                "year": year,
                "pmid": pmid,
                "tag": tag,
                "topic": topic,
                "comment": comment,
                "date_created": str(date_created).split(' ')[0],
                "gene_list": gene_list }
        data.append(row)
        
    sortedData = sorted(sorted(data, key=lambda p: p['citation']), key=lambda p: p['year'], reverse=True)  
    
    return sortedData
    

def get_list_of_papers(request):

    tag = request.matchdict['tag']
    if tag is None:
        return HTTPBadRequest(body=json.dumps({'error': 'No tag is provided'}), content_type='text/json')
    tag = tag.replace('_', ' ').replace('|', '/')

    gene = request.matchdict['gene']
    year = request.matchdict['year']
    if gene in ['none', 'None']:
        gene = None

    dbentity_id = None
    if gene is not None:
        dbentity = None
        if gene.startswith('SGD:S') or gene.startswith('S'):
            sgdid = gene.replace('SGD:', '')
            dbentity = DBSession.query(Locusdbentity).filter_by(sgdid=sgdid).one_or_none()
        if dbentity is None:
            dbentity = DBSession.query(Locusdbentity).filter_by(systematic_name=gene).one_or_none()
            if dbentity is None:
                dbentity = DBSession.query(Locusdbentity).filter_by(gene_name=gene).one_or_none()
        if dbentity is None:
            dbentity = DBSession.query(Dbentity).filter_by(format_name=gene, subclass='COMPLEX').one_or_none()
        if dbentity is None:
            dbentity = DBSession.query(Pathwaydbentity).filter_by(biocyc_id=gene).one_or_none()
        if dbentity is None:
            dbentity = DBSession.query(Dbentity).filter_by(subclass='ALLELE').filter(Dbentity.display_name.ilike(gene)).one_or_none()
        if dbentity is not None:
            dbentity_id = dbentity.dbentity_id
        else:
            HTTPBadRequest(body=json.dumps({'error': 'Gene name/Complex ID/Pathway ID/Allele name ' + gene + ' is not in the database.'}), content_type='text/json')

    ref_ids = []
    if year.isdigit():
        ref_ids = []
        for x in DBSession.query(Referencedbentity).filter_by(year=int(year)).all():
            ref_ids.append(x.dbentity_id)

    curationObjs = None
    if len(ref_ids) > 0 and dbentity_id:
        curationObjs = DBSession.query(CurationReference).filter_by(curation_tag=tag, dbentity_id=dbentity_id).filter(CurationReference.reference_id.in_(ref_ids)).all()
    elif len(ref_ids) > 0:
        curationObjs = DBSession.query(CurationReference).filter_by(curation_tag=tag).filter(CurationReference.reference_id.in_(ref_ids)).all()
    elif dbentity_id:
        curationObjs = DBSession.query(CurationReference).filter_by(curation_tag=tag, dbentity_id=dbentity_id).all()
    else:
        curationObjs = DBSession.query(CurationReference).filter_by(curation_tag=tag).all()

    if curationObjs is None:
        return []

    data = group_papers(curationObjs) 
    
    return HTTPOk(body=json.dumps(data), content_type='text/json')
    
def update_litguide(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])

        gene_id_list = request.params.get('gene_id_list', '')
        tag = request.params.get('tag', '')
        topic = request.params.get('topic', '')
        unlink = request.params.get('unlink', '')

        if gene_id_list == '':
            return HTTPBadRequest(body=json.dumps({'error': "Pick one or more genes"}), content_type='text/json')

        curation_ids = []
        annotation_ids = []
        curation_id_to_gene = {}
        annotation_id_to_gene = {}
        if gene_id_list != '':
            gene_ids = gene_id_list.split(' ')
            for gene_id in gene_ids:
                [gene, curation_id, annotation_id] = gene_id.split('|')
                curation_id = int(curation_id)
                curation_ids.append(curation_id)
                if gene:
                    curation_id_to_gene[curation_id] = gene
                if annotation_id is not None and annotation_id.isdigit():
                    annotation_id = int(annotation_id)
                    annotation_ids.append(annotation_id)
                    if gene:
                        annotation_id_to_gene[annotation_id] = gene

        success_message = ""

        if unlink in ['tag', 'both']:
            for curation_id in curation_ids:
                x = curator_session.query(CurationReference).filter_by(curation_id=curation_id).one_or_none()
                curator_session.delete(x)
                success_message = success_message + "The curation_tag <strong>" + tag + "</strong> is unlinked from gene <strong>" + curation_id_to_gene[curation_id] + "</strong> and this paper. "
                        
        if unlink in ['topic', 'both']:
            for annotation_id in annotation_ids:
                x = curator_session.query(Literatureannotation).filter_by(annotation_id=annotation_id).one_or_none()
                curator_session.delete(x)
                success_message = success_message + "The topic <strong>" + topic + "</strong> is unlinked from gene <strong>" + annotation_id_to_gene[annotation_id] + "</strong> and this paper. "

        if unlink == '':
            for curation_id in curation_ids:
                x = curator_session.query(CurationReference).filter_by(curation_id=curation_id).one_or_none()
                gene = curation_id_to_gene.get(curation_id)
                if x.curation_tag != tag:
                    y = curator_session.query(CurationReference).filter_by(curation_tag=tag, reference_id=x.reference_id, dbentity_id = x.dbentity_id).one_or_none()
                    if y is not None:
                        if gene:
                            success_message = success_message + "The tag <strong>" + tag + "</strong> is already linked with gene <strong>" + gene + "</strong> and this paper. "
                        else:
                            success_message = success_message + "The tag <strong>" + tag + "</strong> is alreadylinked with this paper. "
                    else:
                        if gene:
                            success_message = success_message + "The tag for gene <strong>" + gene + "</strong> has been changed from <strong>" + x.curation_tag + "</strong> to <strong>" + tag + "</strong>. "
                        else:
                            success_message = success_message + "The tag has been changed from <strong>" + x.curation_tag + "</strong> to <strong>" + tag + "</strong>. "
                        x.curation_tag = tag
                        curator_session.add(x)

            for annotation_id in annotation_ids:
                x = curator_session.query(Literatureannotation).filter_by(annotation_id=annotation_id).one_or_none()
                if x.topic != topic:
                    gene = annotation_id_to_gene[annotation_id]
                    y = curator_session.query(Literatureannotation).filter_by(topic=topic, reference_id=x.reference_id, dbentity_id = x.dbentity_id).one_or_none()
                    if y is not None:
                        success_message = success_message + "The topic <strong>" + topic + "</strong> is already linked with gene <strong>" + gene + "</strong> and this paper. "
                    else:
                        success_message = success_message + "The topic for gene <strong>" + gene + "</strong> has been changed from <strong>" + x.topic + "</strong> to <strong>"+ topic + "</strong>. "
                        x.topic = topic
                        curator_session.add(x)

        if success_message == "":
            success_message = "Nothing is changed for tag/topic."
        success_message = success_message + " DONE!"
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'litguide': "LIT_GUIDE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e) + ". DONE reporting ERROR!"}), content_type='text/json')

def add_litguide(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        sgd = DBSession.query(Source).filter_by(display_name='SGD').one_or_none()
        source_id = sgd.source_id

        genes = request.params.get('genes', '')
        pmid = request.params.get('pmid', '')
        tag = request.params.get('tag', '')
        old_tag = request.params.get('old_tag', '') 
        topic = request.params.get('topic', '')
        unlink = request.params.get('unlink', '')

        # return HTTPBadRequest(body=json.dumps({'error': "pmid="+pmid+", unlink="+unlink}), content_type='text/json')

        if pmid == '':
            return HTTPBadRequest(body=json.dumps({'error': "Please enter a PMID."}), content_type='text/json')

        x = curator_session.query(Referencedbentity).filter_by(pmid=int(pmid)).one_or_none()
        if x is None:
            return HTTPBadRequest(body=json.dumps({'error': "The PMID="+pmid+" is not in the database."}), content_type='text/json')
        reference_id = x.dbentity_id

        success_message = ""

        if unlink == 'tag':
            x = curator_session.query(CurationReference).filter_by(curation_tag=old_tag, reference_id=reference_id).one_or_none()
            if x is not None:
                curator_session.delete(x)
                success_message = success_message + "The curation_tag <strong>" + old_tag + "</strong> is unlinked from this paper. "
            else:
                return HTTPBadRequest(body=json.dumps({'error': "The tag <strong>"+old_tag+"</strong> is not linked with pmid="+pmid+". So no need to unlink."}), content_type='text/json')
            
        elif genes == '':
            if old_tag: 
                if old_tag != tag:
                    x = curator_session.query(CurationReference).filter_by(curation_tag=old_tag, reference_id=reference_id).one_or_none()
                    if x is not None:
                        x.curation_tag = tag
                        curator_session.add(x)
                        success_message = success_message + "The tag for this paper has been changed from <strong>" + old_tag + "</strong> to <strong>" + tag + "</strong>. "
            elif tag:
                x = CurationReference(reference_id = reference_id,
                                      source_id = source_id,
                                      curation_tag = tag,
                                      created_by = CREATED_BY)
                curator_session.add(x)
                success_message = success_message + "A new curation_reference row for pmid " + "<strong>" + pmid + "</strong>, and curation_tag <strong>" + tag + "</strong> has been added into the database. "
        else:
            gene_list = genes.replace('|', ' ').split(' ')
            dbentity_id_to_gene = {}
            dbentity_id_list = []
            for gene in gene_list:
                if gene == '':
                    continue
                dbentity = None
                if gene.startswith('SGD:') or gene.startswith('S00'):
                    dbentity = curator_session.query(Locusdbentity).filter_by(sgdid=gene).one_or_none()
                else:
                    dbentity = curator_session.query(Locusdbentity).filter_by(gene_name=gene).one_or_none()
                    if dbentity is None:
                        dbentity = curator_session.query(Locusdbentity).filter_by(systematic_name=gene).one_or_none()
                if dbentity is None:
                    dbentity = curator_session.query(Dbentity).filter_by(format_name=gene, subclass='COOMPLEX').one_or_none()
                if dbentity is None:
                    dbentity = curator_session.query(Pathwaydbentity).filter_by(biocyc_id=gene).one_or_none()
                if dbentity is None:
                    return HTTPBadRequest(body=json.dumps({'error': "The gene " + gene + " you entered is not in the database."}), content_type='text/json')
                dbentity_id_to_gene[dbentity.dbentity_id] = gene
                dbentity_id_list.append(dbentity.dbentity_id)

            taxonomy_id = None
            if topic != '':
                taxon = curator_session.query(Taxonomy).filter_by(taxid=TAXON).one_or_none()
                taxonomy_id = taxon.taxonomy_id

            for dbentity_id in dbentity_id_to_gene:
                if tag != '':
                    x = CurationReference(reference_id = reference_id,
                                          source_id = source_id,
                                          dbentity_id = dbentity_id,
                                          curation_tag = tag,
                                          created_by = CREATED_BY)
                    curator_session.add(x)
                    success_message = success_message + "A new curation_reference row for gene <strong>" + dbentity_id_to_gene[dbentity_id] + "</strong>, pmid " + "<strong>" + pmid + "</strong>, and curation_tag <strong>" + tag + "</strong> has been added into the database. "

                if topic != '':
                    x = Literatureannotation(dbentity_id = dbentity_id,
                                             source_id = source_id,
                                             taxonomy_id = taxonomy_id,
                                             reference_id = reference_id,
                                             topic = topic,
                                             created_by = CREATED_BY)
                    curator_session.add(x)
                    success_message = success_message +"A new literatureannotation row for gene <strong>" + dbentity_id_to_gene[dbentity_id] + "</strong>, pmid " + "<strong>" + pmid +"</strong>, and topic <strong>" + topic +"</strong> has been added into the database. "
            if len(dbentity_id_list) > 0:
                x = curator_session.query(CurationReference).filter_by(curation_tag=old_tag, reference_id=reference_id).one_or_none()
                if x is not None:
                    curator_session.delete(x)
                    success_message = success_message + "The curation_tag <strong>" + old_tag + "</strong> is unlinked from this paper. "

        if success_message == "":
            success_message = "Nothing is changed for tag/topic."
        success_message = success_message + " DONE!"
        transaction.commit()
        return HTTPOk(body=json.dumps({'success': success_message, 'litguide': "LIT_GUIDE"}), content_type='text/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e) + ". DONE reporting ERROR!"}), content_type='text/json')
