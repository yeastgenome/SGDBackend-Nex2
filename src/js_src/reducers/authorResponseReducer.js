const DEFAULT_STATE = {
  currentData: {
    pmid: '',
    email: '',
    citation: '',
    has_novel_research: '0',
    has_large_scale_data: '0',
    has_fast_track_tag: '0',
    curator_checked_datasets: '0',
    curator_checked_genelist: '0',
    no_action_required: '0',
    research_results:     '',
    genes: '',
    dateset_desc: '',
    other_desc: '',
    curation_id: null
  }
};

const SET_AUTHOR_RESPONSE = 'SET_AUTHOR_RESPONSE';

const authorResponseReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_AUTHOR_RESPONSE:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default authorResponseReducer;