import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setFileMetadata} from '../../actions/fileMetadataActions';
import TextFieldSection from '../phenotype/textFieldSection';
const GET_FILE_METADATA = '/get_file_metadata/';

const TIMEOUT = 240000;

class SearchMetadata extends Component {

  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleGetMetadata = this.handleGetMetadata.bind(this);
    
    this.state = {
      isComplete: false,
      metadata: [],
      isLoading: false
    };    
  }

  handleChange() {
    let currentMetadata = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentMetadata[key[0]] = key[1];
    }
    this.props.dispatch(setFileMetadata(currentMetadata));
  }

  handleGetMetadata(){
    let url = this.setGetUrl();
    this.setState({ metadata: [], isLoading: true });
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ metadata: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isLoading: false, isComplete: true }));
  }

  setGetUrl() {
    let query = this.props.metadata['display_name'];
    let url = GET_FILE_METADATA + query;
    if (query == '') {
      this.props.dispatch(setMessage('Please enter the file name.'));
    }
    return url;
  }

  addSubmitButton(name) {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6'>
            <button type='submit' className="button expanded" > {name} </button>
          </div>
        </div>
      </div>
    );
  }

  getCurateLink(sgdid) {
    return (
      <form method='POST' action='/#/edit_file_metadata' target='new'>
        <input type='hidden' name='sgdid' value={sgdid} />
        <input type="submit" value='Curate' />
      </form>
    );
  }
    
  getDataRows(data) {

    window.localStorage.clear();

    let rows = data.map((d, i) => {
      return (
        <tr key={i}>
          <td>{ d.display_name }</td>
          <td>{ d.previous_file_name}</td>
          <td>{ d.year }</td>
          <td><a href={ d.s3_url }>Download file</a></td>
          <td>{ d.description }</td>
          <td><Link to={`/edit_file_metadata/${d.sgdid}`} target='new'><i className='fa fa-edit' /> Curate </Link></td> 
        </tr>
      );
    });
    return rows;
  }

  displayMetadata() {
    let data = this.state.metadata;
    if (data.length > 0) {
      let rows = this.getDataRows(data);
      return (
        <div>	    
          { this.searchForm() }
          <table>
            <thead>
              <tr>
                <th>Display name</th> 
                <th>Previous file name</th>
                <th>Year</th>
                <th>Download file from s3</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              { rows }
            </tbody>
          </table>
        </div>
      );
    }
    else {
      return (
        <div>
          <div>{ this.searchForm() }</div>
          <div> No File found for your input(s).</div>
        </div>
      );
    }
  }

  searchForm() {
    return (
      <div>
        <form onSubmit={this.handleGetMetadata} ref='form'>
            <h4>Search file metadata by file name, PMID, or GEO/SRA/ArrayExpress ID:</h4>
          <TextFieldSection sec_title='' name='display_name' value={this.props.metadata.display_name} onOptionChange={this.handleChange} />
          {this.addSubmitButton('Search')}    
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
	<div>
          <div>Please wait while we are retrieving the file metadata from the database.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayMetadata();
    }
    else {
      return this.searchForm();
    }
  }
}

SearchMetadata.propTypes = {
  dispatch: PropTypes.func,
  metadata: PropTypes.object
};


function mapStateToProps(state) {
  return {
    metadata: state.metadata['currentMetadata']
  };
}

export default connect(mapStateToProps)(SearchMetadata);
