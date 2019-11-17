import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
// import FileUpload from './fileUpload';
import NewPheno from './newPhenotype';

class NewPhenotype extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Add Phenotype</h1>
          <NewPheno />
      </CurateLayout>
    );
  }

}

export default NewPhenotype;