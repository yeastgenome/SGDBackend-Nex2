import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import AddLitGuide from './addLitGuide';

class AddTag extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Add Curation Tag/Topic</h1>
          <AddLitGuide />
      </CurateLayout>
    );
  }

}

export default AddTag;