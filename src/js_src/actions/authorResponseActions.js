const SET_AUTHOR_RESPONSE = 'SET_AUTHOR_RESPONSE';
export function setData(currData) {
  return { type: SET_AUTHOR_RESPONSE, payload: { currentData: currData } };
}