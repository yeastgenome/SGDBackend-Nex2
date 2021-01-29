const SET_FILE_METADATA = 'SET_FILE_METADATA';
export function setFileMetadata(currentMetadata) {
  return { type: SET_FILE_METADATA, payload: { currentMetadata: currentMetadata } };
}
