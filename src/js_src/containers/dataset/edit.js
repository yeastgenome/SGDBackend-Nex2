import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import EditDATASET from './editDataset';

class EditDataset extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Update Dataset</h1>
        <EditDATASET /> 
      </CurateLayout>
    );
  }

}

export default EditDataset;
