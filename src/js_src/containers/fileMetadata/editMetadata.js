import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import Dropzone from 'react-dropzone';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setFileMetadata } from '../../actions/fileMetadataActions';
// import { PREVIEW_URL } from '../../constants.js';
import OneMetadata from './oneMetadata';
import style from './style.css';
const UPDATE_METADATA = '/file_metadata_update';
const DELETE_METADATA = '/file_metadata_delete';
const GET_METADATA = '/get_one_file_metadata';

const TIMEOUT = 300000;

class EditMetadata extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleDelete = this.handleDelete.bind(this);
    this.renderFileDrop = this.renderFileDrop.bind(this);
      
    this.state = {
      file: '',
      isLoading: false,
      isComplete: false,
    };
  }

  componentDidMount() {
    let url = this.setVariables();
    this.getData(url);
  }
    
  handleClear(){
    this.setState({ file: '' });
  }

  handleDrop(files){
    this.setState({ file: files[0] });
  }

  renderFileDrop() {
    if (this.state.file){      
      return(
        <div>
          <p>Uploaded file: {this.state.file.name}</p>
          <a onClick={this.handleClear.bind(this)}>Clear This File</a>
        </div>
      );
    }	
    return  (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          <Dropzone onDrop={this.handleDrop.bind(this)} multiple={false}>
            <p className={style.uploadMsg}>Drop file here or click to select.</p>
            <h3 className={style.uploadIcon}><i className='fa fa-cloud-upload' /></h3>
          </Dropzone>
        </div>
        <div className='columns medium-6 small-6'>Note: No need to upload a file if you only want to update the metadata for this file. If you upload a file and the md5sum is different from the current version, the interface will insert the metadata from this screen into the database, upload this new version to s3, set this version as 'Active', and mark the old version as 'Archived'.
        </div>
      </div>);
  }
    
  handleChange() {
    let currentMetadata = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentMetadata[key[0]] = key[1];
    }
    this.props.dispatch(setFileMetadata(currentMetadata));
  }

  handleUpdate(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.metadata){
      formData.append(key,this.props.metadata[key]);
    }
    // console.log('file=' + this.state.file);
    formData.append('file', this.state.file);
    fetchData(UPDATE_METADATA, {
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
      this.props.dispatch(setMessage(data.success));
    }).catch( (data) => {
      let errorMEssage = data ? data.error: 'Error occured: connection timed out';
      this.props.dispatch(setError(errorMEssage));
      this.setState({ isPending: false});
    });
  }

  handleDelete(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.metadata){
      formData.append(key,this.props.metadata[key]);
    }
    fetchData(DELETE_METADATA, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      timeout: TIMEOUT
    }).then((data) => {
      this.props.dispatch(setMessage(data.success));
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }
    
  addButtons() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpdate.bind(this)} > Update Metadata </button>
          </div>
          <div className='columns medium-6 small-6'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to delete this file along with all the metadata associated with it?')) this.handleDelete(e); }} > Delete this file </button>
          </div>
        </div>
      </div>
    );
  }

  getData(url) {
    this.setState({ isLoading: true });
    fetchData(url).then( (data) => {
      let currentMetadata = {};
      for (let key in data) {
        currentMetadata[key] = data[key];
      }
      this.props.dispatch(setFileMetadata(currentMetadata));
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isComplete: true, isLoading: false }));
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let sgdid = urlList[urlList.length-1];
    let url = GET_METADATA + '/' + sgdid;  
    this.setState({
      sgdid: sgdid,
    });
    return url;
  }

  displayForm() {
    return (
      <div>
        <form onSubmit={this.handleUpdate} ref='form'>
          <input name='sgdid' value={this.props.metadata.sgdid} className="hide" />
          <OneMetadata metadata={this.props.metadata} onOptionChange={this.handleChange} onFileUpload={this.handleFile} />
          {this.renderFileDrop()}
          <hr />
          {this.addButtons()}          	
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
        <div>
          <div>Please wait while we are constructing the update form.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayForm();
    }
    else {
      return (<div>Something is wrong while we are constructing the update form.</div>);
    }
  }
}

EditMetadata.propTypes = {
  dispatch: PropTypes.func,
  metadata: PropTypes.object,
  csrfToken: PropTypes.string
};


function mapStateToProps(state) {
  return {
    metadata: state.metadata['currentMetadata'],
    csrfToken: state.auth.get('csrfToken')
  };
}

export default connect(mapStateToProps)(EditMetadata);
