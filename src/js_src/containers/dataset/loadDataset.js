import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Dropzone from 'react-dropzone';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import style from '../fileMetadata/style.css';
const LOAD_DATASET = '/dataset_load';
const LOAD_SAMPLE = '/datasetsample_load';

const TIMEOUT = 300000;

class LoadDataset extends Component {
  constructor(props) {
    super(props);

    this.handleUpload = this.handleUpload.bind(this);
    this.renderFileDrop = this.renderFileDrop.bind(this);
    this.handleToggleDatasetOrSample = this.handleToggleDatasetOrSample.bind(this);

    this.state = {
      files: [],
      isDataset: true 
    };
  }

  handleToggleDatasetOrSample() {
    this.setState(function(previousState) {
      return { isDataset: !previousState.isDataset, files: [] };
    });
  }
   
  handleClear(){
    this.setState({ files: [] });
  }

  handleDrop(files){
    this.setState({ files: files });
  }

  buttonName() {
    if (this.state.isDataset) {
      return 'Submit Dataset File(s)';
    }
    else {
      return 'Submit Sample File(s)';
    }
  }

  addButton() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpload.bind(this)} > {this.buttonName()} </button>
          </div>
        </div>
      </div>
    );
  }
	
  renderFileDrop() {
    if(this.state.files.length){
      let filenames = this.state.files.map( (file, index) => {
        return <li key={index}>{file.name}</li>;
      }); 
      return(
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <ul>{filenames}</ul>
            <a onClick={this.handleClear.bind(this)}>Clear File(s)</a>
            <hr />
            {this.addButton()}
          </div>
          <div className='columns medium-6 small-6'>
            It will take a while to load data into database...
          </div>
        </div>
      );
    }	
    return  (
      <div className='row'>
        <div className='columns medium-4 small-4'>
          <Dropzone onDrop={this.handleDrop.bind(this)} multiple={true}>
            <p className={style.uploadMsg}>Drop file here or click to select.</p>
            <h3 className={style.uploadIcon}><i className='fa fa-cloud-upload' /></h3>
          </Dropzone>
        </div>
        <div className='columns medium-8 small-8'>
          {this.note()}
        </div>
      </div>);
  }
    
  handleUpload(e) {
    e.preventDefault();
    let load_url = LOAD_SAMPLE;
    if (this.state.isDataset) {
      load_url = LOAD_DATASET;
    }
    let success_message = '';
    let error_message = '';
    this.state.files.map( (file, index) => {
      console.log('uploading file: ' + index + ' ' + file.name);
      let formData = new FormData();
      formData.append('file', file);
      fetchData(load_url, {
        type: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRF-Token': this.props.csrfToken,
        },
        // contentType: file.type,
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

  note() {
    if (this.state.isDataset) {
      return (<div>
        <div><h3>Please upload one or more <strong>dataset</strong> file(s).</h3></div>
        <div><h4>A dataset file has to contain the following tab-delimited fields and the 1st line of the file is the header line:</h4></div>
        <div>dataset.format_name</div>
        <div>dataset.display_name</div>
        <div>dataset.source</div>
        <div>dataset.dbxref_id</div>
        <div>dataset.dbxref_type</div>
        <div>dataset.date_public</div>
        <div>dataset.parent_dataset_id</div>
        <div>taxon_id</div>
        <div>dataset.channel_count</div>
        <div>dataset.sample_count</div>
        <div>dataset.is_in_spell</div>
        <div>dataset.is_in_browser</div>
        <div>dataset_description</div>
        <div>datasetlab.lab_name</div>
        <div>datasetlab.lab_location</div>
        <div>keywords(pipe-delimited)</div>
        <div>pmids(pipe-delimited)</div>
        <div>dbentity.display_name</div>
        <div>dataset_url.obj_url</div>
        <div>dataset_url.url_type</div>
      </div>);
    }
    else {
      return (<div>
        <div><h3>Please upload one or more <strong>dataset sample</strong> file(s).</h3></div>
        <div><h4>A dataset sample file has to contain the following tab-delimited fields and the 1st line of the file is the header line:</h4></div>
        <div>dataset.format_name</div>	
        <div>display_name(sample_title)</div>
        <div>description</div>		
        <div>dbxref_id</div>	
        <div>dbxref_type</div>	
        <div>biosample_name</div>	
        <div>biosample_id</div>
        <div>assay_name</div>
        <div>assay_id</div>
        <div>strain_name</div>	
        <div>sample_order</div>
        <div>taxon_id(optional)</div>
      </div>);
    }
  }
    
  displayForm() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <button type="button" className="button expanded" onClick={this.handleToggleDatasetOrSample} disabled={this.state.isDataset}>Load Dataset</button>
          </div>
          <div className='columns medium-6 small-6 end'>
            <button type="button" className="button expanded" onClick={this.handleToggleDatasetOrSample} disabled={!this.state.isDataset}>Load Dataset Sample</button>
          </div>
        </div>    
        <form onSubmit={this.handleUpload} ref='form'>
          {this.renderFileDrop()}
          <hr />
        </form>
      </div>
    );
  }

  render() {
    return this.displayForm();
  }
}

LoadDataset.propTypes = {
  dispatch: PropTypes.func,
  csrfToken: PropTypes.string
};


function mapStateToProps(state) {
  return {
    csrfToken: state.auth.get('csrfToken')
  };
}

export default connect(mapStateToProps)(LoadDataset);
