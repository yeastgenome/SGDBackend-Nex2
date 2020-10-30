import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { setError } from '../../actions/metaActions';
import { DataList } from 'react-datalist-field';
import fetchData from '../../lib/fetchData';
const GET_OBSERVABLES = '/get_observable';
const GET_ALLELES = '/get_allele';
const GET_REPORTERS = '/get_reporter';
const GET_ALLELE_TYPES = '/get_allele_types';

class AutocompleteSection extends Component {
  constructor(props) {
    super(props);
    this.state = {
      options: []
    };
  }

  componentDidMount() {
    if (this.props.id == 'observable_id') {
      this.getData(GET_OBSERVABLES);
    }
    else if (this.props.id == 'allele_id') {
      this.getData(GET_ALLELES);
    }
    else if (this.props.id == 'reporter_id') {
      this.getData(GET_REPORTERS);
    }
    else if (this.props.id == 'so_id') {
      this.getData(GET_ALLELE_TYPES);
    }
    else {
      this.props.dispatch(setError('Unknown ID: ' + this.props.id));
    }
  }

  getData(url) {
    fetchData(url, {
      type: 'GET'
    }).then(data => {
      this.setState({ options: data});
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  render() {
    if (this.props.id == 'so_id') {
      return (	  
        <div className='row'>
          {
            this.state.options.length > 0?
            <DataList options={this.state.options} id={this.props.id} left={this.props.value1} right={this.props.value2} selectedIdName={this.props.selectedIdName} onOptionChange={this.props.onOptionChange} selectedId={this.props.selectedId} placeholder={this.props.placeholder} setNewValue={this.props.setNewValue} />
            :''
          }
        </div>
      );	  
    }      
    return (
      <div className='row'>
        <div className='columns medium-12'>
          <div className='row'>
            <div className='columns medium-12'>
              <label> { this.props.sec_title } </label>
            </div>
          </div>
          <div className='row'>
            {
              this.state.options.length > 0?
              <DataList options={this.state.options} id={this.props.id} left={this.props.value1} right={this.props.value2} selectedIdName={this.props.selectedIdName} onOptionChange={this.props.onOptionChange} selectedId={this.props.selectedId} placeholder={this.props.placeholder} setNewValue={this.props.setNewValue} />
              :''
            }
          </div>
        </div>
      </div>
    );
  }
}

AutocompleteSection.propTypes = {
  dispatch: PropTypes.func,
  sec_title: PropTypes.string,
  id: PropTypes.string,
  value1: PropTypes.string,
  value2: PropTypes.string,
  onOptionChange: PropTypes.func,
  selectedIdName: PropTypes.string,
  selectedId: PropTypes.string,
  placeholder: PropTypes.string,
  setNewValue:PropTypes.bool
};

export default AutocompleteSection;
