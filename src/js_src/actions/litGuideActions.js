const SET_LITGUIDE = 'SET_LITGUIDE';
export function setData(currData) {
  return { type: SET_LITGUIDE, payload: { curationData: currData } };
}
