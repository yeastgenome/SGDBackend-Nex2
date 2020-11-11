const DEFAULT_STATE = {
  currentAllele: {
    dbentity_id: 0,
    allele_name: '',
    allele_name_pmids: '',
    affected_gene: '',
    affected_gene_pmids:'',
    so_id: '',
    allele_type_pmids: '',
    description: '',
    description_pmids: '',
    aliases: '',
    alias_pmids: ''
  }
};

const SET_ALLELE = 'SET_ALLELE';

const alleleReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_ALLELE:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default alleleReducer;
