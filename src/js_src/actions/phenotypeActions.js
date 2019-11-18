const SET_PHENOTYPE = 'SET_PHENOTYPE';
export function setPhenotype(currentPhenotype) {
  return { type: SET_PHENOTYPE, payload: { currentPhenotype: currentPhenotype } };
}