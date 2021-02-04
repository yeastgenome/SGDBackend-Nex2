import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import EditMETADATA from './editMetadata';

class EditMetadata extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Update File Metadata</h1>
        <EditMETADATA /> 
      </CurateLayout>
    );
  }

}

export default EditMetadata;
