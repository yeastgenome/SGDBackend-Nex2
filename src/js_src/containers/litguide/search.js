import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import SearchLitGuide from './searchLitGuide';

class SearchLitTodo extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>SGD Literature TODO List</h1>
          <SearchLitGuide />
      </CurateLayout>
    );
  }

}

export default SearchLitTodo;
