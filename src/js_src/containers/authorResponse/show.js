import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import ShowAllResponses from './showAllResponses';

class ShowAll extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Author Responses</h1>
          <ShowAllResponses />
      </CurateLayout>
    );
  }

}

export default ShowAll;
