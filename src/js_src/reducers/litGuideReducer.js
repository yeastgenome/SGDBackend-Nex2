const DEFAULT_STATE = {
  curationData: {
    year: '',
    tag: '',
    gene: '',
    genes: '',
    topic: '',
    pmid: '',
    old_tag: ''
  }
};

const SET_LITGUIDE = 'SET_LITGUIDE';

const litGuideReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_LITGUIDE:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default litGuideReducer;