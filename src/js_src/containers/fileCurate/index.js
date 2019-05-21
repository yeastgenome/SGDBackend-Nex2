/* eslint-disable no-debugger */
/* eslint-disable no-unused-vars */
import React, {Component} from 'react';
import FileCurateForm from '../../components/fileCurate/fileCurateForm';
import CurateLayout from '../curateHome/layout';

/**
 * @summary File Curation container component
 * @author fgondwe
 * Notes:
 *      user should be able to update a readmefile, comments for instance.
 *      update readmefile automatically with s3 urls.
 */
class FileCurate extends Component {
  constructor(props){
    super(props);
    this.handleFileUploadSubmit = this.handleFileUploadSubmit.bind(this);
  }
  handleFileUploadSubmit(e){
    console.log(e);
    //e.prevenyDefault();
    //let formData = new FormData(this.refs.form);

  }

  render(){
    return (<CurateLayout><div className='row'><FileCurateForm onFileUploadSubmit={this.handleFileUploadSubmit} /></div></CurateLayout>);
  }
}


export default FileCurate;
