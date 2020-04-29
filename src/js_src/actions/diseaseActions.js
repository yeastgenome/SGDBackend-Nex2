const SET_DISEASE = 'SET_DISEASE';
export function setDisease(currentDisease) {
  return { type: SET_DISEASE, payload: { currentDisease: currentDisease } };
}