import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setDataset } from '../../actions/datasetActions';
import TextFieldSection from '../phenotype/textFieldSection';
const GET_DATASETS = '/get_datasets/';

const TIMEOUT = 240000;

class SearchDataset extends Component {

  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleGetDatasets = this.handleGetDatasets.bind(this);
    
    this.state = {
      isComplete: false,
      datasetData: [],
      isLoading: false
    };    
  }

  handleChange() {
    let currentDataset = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentDataset[key[0]] = key[1];
    }
    this.props.dispatch(setDataset(currentDataset));
  }

  handleGetDatasets(){
    let url = this.setGetUrl();
    this.setState({ datasetData: [], isLoading: true });
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ datasetData: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isLoading: false, isComplete: true }));
  }

  setGetUrl() {
    let dataset_query = this.props.dataset['format_name'];
    if (dataset_query) {
      return GET_DATASETS + dataset_query;
    }	
    else {
      this.props.dispatch(setMessage('Please enter an dataset name.'));
    }
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

  getDataRows(data) {
    let rows = data.map((d, i) => {
      let linkUrl = '/curate/dataset/' + d.format_name;
      return (
        <tr key={i}>
          <td>{ d.format_name }</td>
          <td>{ d.display_name }</td>
          <td>{ d.keywords }</td>
          <td>{ d.pmids }</td>
          <td><Link to={ linkUrl } target='new'><i className='fa fa-edit' /> Curate </Link></td>
        </tr>
      );
    });
    return rows;
  }
    
  displayDatasets() {
    let data = this.state.datasetData; 
    if (data.length > 0) {
      let rows = this.getDataRows(data);	
      return (
        <div>	    
          { this.searchForm() }
          <table>
            <thead>
              <tr>
                <th>Format name</th> 
                <th>Display name</th>
                <th>Keyword(s)</th>
                <th>PMID(s)</th>
                <th>Actions</th>
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
          <div> No datasets found for your input(s).</div>
        </div>
      );
    }
  }

  searchForm() {
    return (
      <div>
        <form onSubmit={this.handleGetDatasets} ref='form'>
          <h4>Search datasets:</h4>
          <TextFieldSection sec_title='Dataset ID' name='format_name' value={this.props.dataset.format_name} onOptionChange={this.handleChange} />
          {this.addSubmitButton('Search')}    
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
	<div>
          <div>Please wait while we are retrieving the dataset data from the database.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayDatasets();
    }
    else {
      return this.searchForm();
    }
  }
}

SearchDataset.propTypes = {
  dispatch: PropTypes.func,
  dataset: PropTypes.object
};


function mapStateToProps(state) {
  return {
    dataset: state.dataset['currentDataset']
  };
}

export default connect(mapStateToProps)(SearchDataset);
