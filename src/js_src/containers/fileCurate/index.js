
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
  }

  render(){
    return (<CurateLayout><FileCurateForm /></CurateLayout>);
  }
}

export default FileCurate;
