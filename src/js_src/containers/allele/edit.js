import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import EditALLELE from './editAllele';

class EditAllele extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Update or Delete Allele</h1>
        <EditALLELE /> 
      </CurateLayout>
    );
  }

}

export default EditAllele;
