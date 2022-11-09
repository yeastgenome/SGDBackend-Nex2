export function setError (message) {
  return { type: 'SET_ERROR', payload: message };
}

export function clearError () {
  return { type: 'CLEAR_ERROR' };
}

export function setMessage (message) {
  return { type: 'SET_MESSAGE', payload: message };
}

export function clearMessage () {
  return { type: 'CLEAR_MESSAGE' };
}

export function setNotReady () {
  return { type: 'SET_NOT_READY' };
}

export function setPending () {
  return { type: 'SET_PENDING' };
}

export function setReady () {
  return { type: 'SET_READY' };
}

export function finishPending () {
  return { type: 'FINISH_PENDING' };
}

export function updateColleagueCount(count){
  return {type:'UPDATE_COLLEAGUE_COUNT',payload:count};
}

export function updateGeneCount(count){
  return {type:'UPDATE_GENE_COUNT',payload:count};
}

export function updateAuthorResponseCount(count){
  return {type:'UPDATE_AUTHOR_RESPONSE_COUNT',payload:count};
}
