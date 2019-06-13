/* eslint-disable no-debugger */
/* eslint-disable no-unused-vars */
/**
 * @summary File Curation container component
 * @author fgondwe
 * Notes:
 *      user should be able to update a readmefile, comments for instance.
 *      update readmefile automatically with s3 urls.
 */
import React, {Component} from 'react';
import FileCurateForm from '../../components/fileCurate/fileCurateForm';
import { connect } from 'react-redux';
import CurateLayout from '../curateHome/layout';
import fetchData from '../../lib/fetchData';
import { clearError, setError } from '../../actions/metaActions';

const UPLOAD_URL = '/upload_file_curate';
const UPLOAD_TIMEOUT = 120000;

class FileCurate extends Component {
  constructor(props){
    super(props);
    this.state = {
      files: [],
      isPending: false
    };
    this.handleFileUploadSubmit = this.handleFileUploadSubmit.bind(this);
  }
  handleFileUploadSubmit(e){
    this.uploadData(e);
  }

  uploadData(formData){
    this.setState({ isPending: true});
    fetchData(UPLOAD_URL, {
      type: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRF-Token': this.props.csrfToken
      },
      data: formData,
      processData: false,
      contentType: false,
      timeout: UPLOAD_TIMEOUT
    }).then( (data) => {
      this.setState({
        isPending: false,
      });

    }).catch( (data) => {
      let errorMEssage = data ? data.error: 'Error occured';
      this.props.dispatch(setError(errorMEssage));
      this.setState({ isPending: false});
    });
    //fetchData

  }

  render(){
    return (<CurateLayout><div className='row'><FileCurateForm onFileUploadSubmit={this.handleFileUploadSubmit} /></div></CurateLayout>);
  }
}

FileCurate.propTypes = {
  csrfToken: React.PropTypes.string,
  dispatch: React.PropTypes.func
};

function mapStateToProps(state) {
  return {
    csrfToken: state.auth.csrfToken
  };
}

export { FileCurate as FileCurate };
export default connect(mapStateToProps)(FileCurate);
