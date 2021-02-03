const DEFAULT_STATE = {
  currentMetadata: {
    dbentity_id: 0,
    display_name: '',
    previous_file_name: '',
    is_in_browser: '',
    is_in_spell: '',
    is_public: '',
    topic_id: '',
    data_id: '',
    format_id: '',
    file_extension: '',
    file_date: '',
    description: '',
    year: '',
    file_size: '',
    readme_file_id: '',
    s3_url: '',
    path: '',
    keywords: '',
    pmids: '',
    sgdid: '',
    dbentity_status: ''
  }
};

const SET_FILE_METADATA = 'SET_FILE_METADATA';

const fileMetadataReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_FILE_METADATA:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default fileMetadataReducer;
