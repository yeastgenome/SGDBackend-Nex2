const SET_DATASET = 'SET_DATASET';
export function setDataset(currentDataset) {
  return { type: SET_DATASET, payload: { currentDataset: currentDataset } };
}
