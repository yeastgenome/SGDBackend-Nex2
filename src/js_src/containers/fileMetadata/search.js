import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import SearchMETADATA from './searchMetadata';

class SearchMetadata extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Search/Update File Metadata</h1>
          <SearchMETADATA />
      </CurateLayout>
    );
  }

}

export default SearchMetadata;
