import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import SearchALLELE from './searchAllele';

class SearchAllele extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Search/Update Allele</h1>
        <SearchALLELE />
      </CurateLayout>
    );
  }

}

export default SearchAllele;
