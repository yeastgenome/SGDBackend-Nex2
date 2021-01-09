import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import FileUpload from './fileUpload';
import ComplementForm from './complementForm';

class Complement extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <div className='row'>
          <div className='columns small-12 medium-12 large-5'>
            <h1> file upload</h1>
            <FileUpload />
          </div>
          <div className='columns small-12 medium-12 large-5 end'>
            <h1>Add/Update complement</h1>
            <ComplementForm />
          </div>
        </div>
      </CurateLayout>
    );
  }

}

export default Complement;