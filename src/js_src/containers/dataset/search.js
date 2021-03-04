import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import SearchDATASET from './searchDataset';

class SearchDataset extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Search/Update Dataset</h1>
        <SearchDATASET />
      </CurateLayout>
    );
  }

}

export default SearchDataset;
