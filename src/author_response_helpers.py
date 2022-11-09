from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from sqlalchemy.exc import IntegrityError, DataError
import transaction
import json
from pyramid.response import Response
from validate_email import validate_email
from src.models import DBSession, Authorresponse, Referencedbentity, Source
from src.curation_helpers import get_curator_session, get_pusher_client

def get_author_responses(curation_id=None):

    try:
        all = None
        if curation_id is None:
            all = DBSession.query(Authorresponse).filter_by(no_action_required = False).all()
        else:
            all = DBSession.query(Authorresponse).filter_by(curation_id=int(curation_id)).all()
        data = []
        for row in all:
            reference_id = None
            if curation_id is not None:
                r = DBSession.query(Referencedbentity).filter_by(pmid=int(row.pmid)).one_or_none()
                if r is not None:
                    reference_id = r.dbentity_id
            if row.curator_checked_datasets == True and curator_checked_genelist == True:
                continue
            genes = row.gene_list
            if row.gene_list:
                genes = genes.replace('|', ' ')
            data.append({ 'curation_id': row.curation_id,
                          'author_email': row.author_email,
                          'pmid': row.pmid,
                          'no_action_required': row.no_action_required,
                          'has_novel_research': row.has_novel_research,
                          'has_large_scale_data': row.has_large_scale_data,
                          'has_fast_track_tag': row.has_fast_track_tag,
                          'curator_checked_datasets': row.curator_checked_datasets,
                          'curator_checked_genelist': row.curator_checked_genelist,
                          'research_results': row.research_results,
                          'gene_list': genes,
                          'dataset_description': row.dataset_description,
                          'other_description': row.other_description,
                          'date_created': str(row.date_created).split(' ')[0] })
        if curation_id is not None:
            row = data[0]
            row['reference_id'] = reference_id
            return Response(body=json.dumps(row), content_type='application/json')
        else:
            return Response(body=json.dumps(data), content_type='application/json')
    except Exception as e:
        return HTTPBadRequest(body=json.dumps({'error': str(e)}))

def set_val(val):
    if val or val is True:
        return '1'
    else:
        return '0'
    
def update_author_response(request):

    try:
        CREATED_BY = request.session['username']
        curator_session = get_curator_session(request.session['username'])
        
        curation_id = request.params.get('curation_id')
        
        has_fast_track_tag = set_val(request.params.get('has_fast_track_tag'))
        curator_checked_datasets = set_val(request.params.get('curator_checked_datasets'))
        curator_checked_genelist = set_val(request.params.get('curator_checked_genelist'))
        no_action_required = set_val(request.params.get('no_action_required'))

        row = curator_session.query(Authorresponse).filter_by(curation_id=int(curation_id)).one_or_none()
    
        cols_changed = []
        if set_val(row.has_fast_track_tag) != has_fast_track_tag:
            row.has_fast_track_tag = has_fast_track_tag
            cols_changed.append('has_fast_track_tag')
        if set_val(row.curator_checked_datasets) != curator_checked_datasets:
            row.curator_checked_datasets = curator_checked_datasets
            cols_changed.append('curator_checked_datasets')
        if set_val(row.curator_checked_genelist) != curator_checked_genelist:
            row.curator_checked_genelist = curator_checked_genelist
            cols_changed.append('curator_checked_genelist')
        if set_val(row.no_action_required) != no_action_required:
            row.no_action_required = no_action_required
            cols_changed.append('no_action_required')

        if len(cols_changed) > 0:
            curator_session.add(row)
            transaction.commit()
            success_message = "The column <strong>" + ", ".join(cols_changed) + "</strong> got updated in authorresponse table."
        else:
            success_message = "Nothing is changed in authorresponse table."
        authorResponseCount = DBSession.query(Authorresponse).filter_by(no_action_required = '0').count()
        pusher = get_pusher_client()
        pusher.trigger('sgd','authorResponseCount',{'message':authorResponseCount})
        return HTTPOk(body=json.dumps({'success': success_message, 'authorResponse': "AUTHORRESPONSE"}), content_type='text/json')
    except Exception as e:
        transaction.abort()
        return HTTPBadRequest(body=json.dumps({'error': "ERROR: " + str(e)}), content_type='text/json')


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

        has_novel_research = False
        if request.params.get('has_novel_research'):
            has_novel_research = True
        has_large_scale_data = False
        if request.params.get('has_large_scale_data'):
            has_large_scale_data = True

        research_results = request.params.get('research_result')
        dataset_description = request.params.get('dataset_desc')
        gene_list = request.params.get('genes')
        other_description = request.params.get('other_desc')

        x = Authorresponse(source_id = source_id,
                           pmid = pmid,
                           author_email = email,
                           has_novel_research = has_novel_research,
                           has_large_scale_data = has_large_scale_data,
                           has_fast_track_tag = False,
                           curator_checked_datasets = False,
                           curator_checked_genelist = False,
                           no_action_required = False,
                           research_results = research_results,
                           gene_list = gene_list,
                           dataset_description = dataset_description,
                           other_description = other_description,
                           created_by = created_by)

        DBSession.add(x)
        transaction.commit()
        authorResponseCount = DBSession.query(Authorresponse).filter_by(no_action_required = '0').count()
        pusher = get_pusher_client()
        pusher.trigger('sgd','authorResponseCount',{'message':authorResponseCount})
        return {'curation_id': 0}
    except Exception as e:
        transaction.abort()
        return HTTPBadRequest(body=json.dumps({'error': "ERROR: " + str(e)}), content_type='text/json')


