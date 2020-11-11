import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import NewALLELE from './newAllele';

class NewAllele extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Add Allele</h1>
        <NewALLELE />
      </CurateLayout>
    );
  }

}

export default NewAllele;
