const SET_COMPLEMENT = 'SET_COMPLEMENT';
export function setComplement(currentComplement) {
  return { type: SET_COMPLEMENT, payload: { currentComplement: currentComplement } };
}