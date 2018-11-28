/**
 * purpose: File Curation container component
 * author: fgondwe
 * Notes:
 *      user should be able to update a readmefile, comments for instance.
 *      update readmefile automatically with s3 urls.
*/
import React, {Component} from 'react';
import CurateLayout from '../curateHome/layout';


class FileCurate extends Component {
  constructor(props){
    super(props);
  }

  render(){
    return (<CurateLayout><p>File curate interface</p></CurateLayout>);
  }
}

export default FileCurate;
