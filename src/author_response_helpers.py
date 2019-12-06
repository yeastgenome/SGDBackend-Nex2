from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from pyramid.response import Response
from validate_email import validate_email
from src.models import DBSession, Authorresponse, Referencedbentity, Source
from src.curation_helpers import get_curator_session

def get_author_responses(curation_id=None):

    try:
        all = None
        if curation_id is None:
            all = DBSession.query(Authorresponse).filter_by(no_action_required = '0').all()
        else:
            all = DBSession.query(Authorresponse).filter_by(curation_id=int(curation_id)).all()
        data = []
        for x in all:
            reference_id = None
            if curation_id is not None:
                r = DBSession.query(Referencedbentity).filter_by(pmid=int(x.pmid)).one_or_none()
                if r is not None:
                    reference_id = r.dbentity_id
            if x.curator_checked_datasets == '1' and curator_checked_genelist == '1':
                continue
            genes = x.gene_list
            if x.gene_list:
                genes = genes.replace('|', ' ')
            data.append({ 'curation_id': x.curation_id,
                          'author_email': x.author_email,
                          'pmid': x.pmid,
                          'no_action_required': x.no_action_required,
                          'has_novel_research': x.has_novel_research,
                          'has_large_scale_data': x.has_large_scale_data,
                          'has_fast_track_tag': x.has_fast_track_tag,
                          'curator_checked_datasets': x.curator_checked_datasets,
                          'curator_checked_genelist': x.curator_checked_genelist,
                          'research_results': x.research_results,
                          'gene_list': genes,
                          'dataset_description': x.dataset_description,
                          'other_description': x.other_description,
                          'date_created': str(x.date_created).split(' ')[0] })
        if curation_id is not None:
            row = data[0]
            row['reference_id'] = reference_id
            return Response(body=json.dumps(row), content_type='application/json')
        else:
            return Response(body=json.dumps(data), content_type='application/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))

def insert_author_response(request):

    try:
        sgd = DBSession.query(Source).filter_by(display_name='Direct submission').one_or_none()
        source_id = sgd.source_id
        created_by = 'OTTO'

        email = request.params.get('email')
        if email == '':
            return HTTPBadRequest(body=json.dumps({'error': "Please enter your email address."}), content_type='text/json')
        is_email_valid = validate_email(email, verify=False)
        if not is_email_valid:
            msg = email + ' is not a valid email.'
            return HTTPBadRequest(body=json.dumps({'error': msg}), content_type='text/json')

        pmid = request.params.get('pmid')
        pmid = pmid.replace('PMID:', '').replace('Pubmed ID:', '').strip()
        if pmid == '':
            return HTTPBadRequest(body=json.dumps({'error': "Please enter Pubmed ID for your paper."}), content_type='text/json')
        if pmid.isdigit():
            pmid = int(pmid)
        else:
            return HTTPBadRequest(body=json.dumps({'error': "Please enter a number for Pubmed ID."}), content_type='text/json')

        x = DBSession.query(Authorresponse).filter_by(author_email=email, pmid=int(pmid)).one_or_none()
        if x is not None:
            return HTTPBadRequest(body=json.dumps({'error': "You have already subomitted info for PMID:" + str(pmid)+"."}), content_type='text/json')

        has_novel_research = '0'
        if request.params.get('has_novel_research'):
            has_novel_research = '1'
        has_large_scale_data = '0'
        if request.params.get('has_large_scale_data'):
            has_large_scale_data = '1'

        research_results = request.params.get('research_result')
        dataset_description = request.params.get('dataset_desc')
        gene_list = request.params.get('genes')
        other_description = request.params.get('other_desc')

        x = Authorresponse(source_id = source_id,
                           pmid = pmid,
                           author_email = email,
                           has_novel_research = has_novel_research,
                           has_large_scale_data = has_large_scale_data,
                           has_fast_track_tag = '0',
                           curator_checked_datasets = '0',
                           curator_checked_genelist = '0',
                           no_action_required = '0',
                           research_results = research_results,
                           gene_list = gene_list,
                           dataset_description = dataset_description,
                           other_description = other_description,
                           created_by = created_by)

        DBSession.add(x)
        transaction.commit()
        return {'curation_id': 0}
    except Exception as e:
        transaction.abort()
        return HTTPBadRequest(body=json.dumps({'error': "ERROR: " + str(e)}), content_type='text/json')


