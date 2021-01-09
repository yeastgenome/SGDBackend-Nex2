const DEFAULT_STATE = {
  currentComplement: {
    annotation_id: 0,
    dbentity_id: '',
    source_id: '',
    taxonomy_id: '',
    reference_id: '',
    ro_id: '',
    eco_id: '',
    obj_url: '',
    direction: '',
    dbxref_id: '',
    curator_comment: ''
  }
};

const SET_COMPLEMENT = 'SET_COMPLEMENT';

const complementReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_COMPLEMENT:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default complementReducer;