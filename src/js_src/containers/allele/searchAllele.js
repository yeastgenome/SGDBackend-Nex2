import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setAllele } from '../../actions/alleleActions';
import TextFieldSection from '../phenotype/textFieldSection';
const GET_ALLELES = '/get_alleles/';

const TIMEOUT = 240000;

class SearchAllele extends Component {

  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleGetAlleles = this.handleGetAlleles.bind(this);
    
    this.state = {
      isComplete: false,
      alleleData: [],
      isLoading: false
    };    
  }

  handleChange() {
    let currentAllele = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentAllele[key[0]] = key[1];
    }
    this.props.dispatch(setAllele(currentAllele));
  }

  handleGetAlleles(){
    let url = this.setGetUrl();
    this.setState({ alleleData: [], isLoading: true });
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ alleleData: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isLoading: false, isComplete: true }));
  }

  setGetUrl() {
    let allele_query = this.props.allele['allele_name'];
    if (allele_query) {
      return GET_ALLELES + allele_query;
    }	
    else {
      this.props.dispatch(setMessage('Please enter an allele name.'));
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
      let linkUrl = '/curate/allele/' + d.format_name;
      return (
        <tr key={i}>
          <td>{ d.allele_name }</td>
          <td>{ d.allele_type }</td>
          <td>{ d.description}</td>
          <td><Link to={ linkUrl } target='new'><i className='fa fa-edit' /> Curate </Link></td>
        </tr>
      );
    });
    return rows;
  }
    
  displayAlleles() {
    let data = this.state.alleleData; 
    if (data.length > 0) {
      let rows = this.getDataRows(data);	
      return (
        <div>	    
          { this.searchForm() }
          <table>
            <thead>
              <tr>
                <th>Allele name</th> 
                <th>Allele type</th>
                <th>Description</th>
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
          <div> No alleles found for your input(s).</div>
        </div>
      );
    }
  }

  searchForm() {
    return (
      <div>
        <form onSubmit={this.handleGetAlleles} ref='form'>
          <h4>Search alleles:</h4>
          <TextFieldSection sec_title='Allele name' name='allele_name' value={this.props.allele.allele_name} onOptionChange={this.handleChange} />
          {this.addSubmitButton('Search')}    
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
	<div>
          <div>Please wait while we are retrieving the allele data from the database.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayAlleles();
    }
    else {
      return this.searchForm();
    }
  }
}

SearchAllele.propTypes = {
  dispatch: PropTypes.func,
  allele: PropTypes.object
};


function mapStateToProps(state) {
  return {
    allele: state.allele['currentAllele']
  };
}

export default connect(mapStateToProps)(SearchAllele);
