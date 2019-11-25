import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import SearchPheno from './searchPhenotype';

class SearchPhenotype extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Search/Update Phenotype</h1>
          <SearchPheno />
      </CurateLayout>
    );
  }

}

export default SearchPhenotype;