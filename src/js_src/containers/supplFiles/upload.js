import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import UploadFiles from './uploadFiles';

class Upload extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Upload Supplemental Files to s3</h1>
        <UploadFiles /> 
      </CurateLayout>
    );
  }

}

export default Upload;
