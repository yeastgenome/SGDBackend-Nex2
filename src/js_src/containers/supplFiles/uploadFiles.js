import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Dropzone from 'react-dropzone';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import style from '../fileMetadata/style.css';
const UPLOAD_FILE = '/upload_suppl_file';

const TIMEOUT = 300000;

class UploadFiles extends Component {
  constructor(props) {
    super(props);

    this.handleUpload = this.handleUpload.bind(this);
    this.renderFileDrop = this.renderFileDrop.bind(this);
      
    this.state = {
      files: []
    };
  }
    
  handleClear(){
    this.setState({ files: [] });
  }

  handleDrop(files){
    this.setState({ files: files });
  }

  renderFileDrop() {
    if(this.state.files.length){
      let filenames = this.state.files.map( (file, index) => {
        return <li key={index}>{file.name}</li>;
      }); 
      return(
        <div>
          <ul>{filenames}</ul>
          <a onClick={this.handleClear.bind(this)}>Clear File(s)</a>
        </div>
      );
    }	
    return  (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          <Dropzone onDrop={this.handleDrop.bind(this)} multiple={true}>
            <p className={style.uploadMsg}>Drop file here or click to select.</p>
            <h3 className={style.uploadIcon}><i className='fa fa-cloud-upload' /></h3>
          </Dropzone>
        </div>
        <div className='columns medium-6 small-6'>It will take a while to upload the files.
        </div>
      </div>);
  }
    
  handleUpload(e) {
    e.preventDefault();
    let success_message = '';
    let error_message = '';
    this.state.files.map( (file, index) => {
      console.log('uploading file: ' + index + ' ' + file.name);
      let formData = new FormData();
      formData.append('file', file);
      fetchData(UPLOAD_FILE, {
        type: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRF-Token': this.props.csrfToken
        },
        data: formData,
        processData: false,
        contentType: false,
        timeout: TIMEOUT
      }).then((data) => {
        success_message = success_message + data.success;
        this.props.dispatch(setMessage(success_message));
      }).catch( (data) => {
        let errorMessage = data ? data.error: 'Error occured: connection timed out';
        error_message = error_message + errorMessage;
        this.props.dispatch(setError(error_message));
      });
    });
  }

  addButton() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpload.bind(this)} > Upload Files </button>
          </div>
        </div>
      </div>
    );
  }
    
  displayForm() {
    return (
      <div>
        <form onSubmit={this.handleUpload} ref='form'>
          {this.renderFileDrop()}
          <hr />
          {this.addButton()}
          <hr />
          Note: This interface is only for uploading the supplemental files to s3 so the expected file name should be like PMID.zip (eg, 33472078.zip). The interface assumes the associated paper should be in the database so it can link the file to the given paper. Also it will take a while to upload the files to s3 so be patient! =)
        </form>
      </div>
    );
  }

  render() {
    return this.displayForm();
  }
}

UploadFiles.propTypes = {
  dispatch: PropTypes.func,
  csrfToken: PropTypes.string
};


function mapStateToProps(state) {
  return {
    csrfToken: state.auth.get('csrfToken')
  };
}

export default connect(mapStateToProps)(UploadFiles);
