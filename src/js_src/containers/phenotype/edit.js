import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import EditPheno from './editPhenotype';

class EditPhenotype extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Update or Delete Phenotype</h1>
          <EditPheno />
      </CurateLayout>
    );
  }

}

export default EditPhenotype;