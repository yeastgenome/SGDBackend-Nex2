const DEFAULT_STATE = {
  currentDataset: {
    dataset_id: 0,
    format_name: '',
    display_name: '',
    obj_url: '',
    dbxref_id:'',
    dbxref_type: '',
    date_public: '',
    parent_dataset_id: '',
    channel_count: '',
    sample_count: '',
    is_in_spell: '',
    is_in_browser: '',
    description: '',
    filenames: '',
    keywords: '',
    pmids: '',
    url1: '',
    url2: '',
    url3: '',
    lab1: '',
    lab2: ''
  }
};

const SET_DATASET = 'SET_DATASET';

const datasetReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_DATASET:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default datasetReducer;
