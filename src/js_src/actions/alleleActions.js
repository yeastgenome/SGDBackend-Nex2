const SET_ALLELE = 'SET_ALLELE';
export function setAllele(currentAllele) {
  return { type: SET_ALLELE, payload: { currentAllele: currentAllele } };
}
