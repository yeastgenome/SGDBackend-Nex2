import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import FileUpload from './fileupload';
import PtmForm from './ptmForm';

class PostTranslationModification extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <div className="row">
          <div className="columns large-6">
            <h1>PTM file upload</h1>
            <FileUpload />
          </div>
          
          <div className="columns large-6">
            <h1>Add single value</h1>

            <PtmForm />

          </div>
        </div>
      </CurateLayout>
    );
  }

}

export default PostTranslationModification;