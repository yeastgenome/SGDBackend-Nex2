const DEFAULT_STATE = {
  currentPhenotype: {
    annotation_id: 0,
    genes: '',
    reference: '',
    gene_list: '',
    taxonomy_id:'',
    reference_id: '',
    experiment_id: '',
    mutant_id: '',
    qualifier_id: '',
    observable_id: '',
    strain_background: '',
    strain_name: '',
    experiment_comment: '',
    details: '',
    allele_id: '',
    allele_comment: '',
    reporter_id: '',
    reporter_comment: '',
    chemical_name: '',
    chemical_value: '',
    chemical_unit: '',
    media_name: '',
    media_value: '',
    media_unit: '',
    temperature_name: '',
    temperature_value: '',
    temperature_unit: '',
    treatment_name: '',
    treatment_value: '',
    treatment_unit: '',
    assay_name: '',
    assay_value: '',
    assay_unit: '',
    phase_name: '',
    phase_value: '',
    phase_unit: '',
    radiation_name: '',
    radiation_value: '',
    radiation_unit: ''
  }
};

const SET_PHENOTYPE = 'SET_PHENOTYPE';

const phenotypeReducer = (state = DEFAULT_STATE, action) => {
  switch (action.type) {
  case SET_PHENOTYPE:
    return Object.assign({}, state, action.payload);
  default:
    return state;
  }
};

export default phenotypeReducer;