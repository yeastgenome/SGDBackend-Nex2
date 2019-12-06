import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import EditLitGuide from './editLitGuide';

class EditTag extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Update or Unlink Curation Tag/Topic</h1>
          <EditLitGuide />
      </CurateLayout>
    );
  }

}

export default EditTag;