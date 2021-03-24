import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { setError } from '../../actions/metaActions';
import { DataList } from 'react-datalist-field';
import fetchData from '../../lib/fetchData';
const GET_OBSERVABLES = '/get_observable';
const GET_ALLELES = '/get_allele';
const GET_REPORTERS = '/get_reporter';
const GET_ALLELE_TYPES = '/get_allele_types';
const GET_EDAM_DATA = '/get_edam/data';
const GET_EDAM_TOPIC = '/get_edam/topic';
const GET_EDAM_FORMAT = '/get_edam/format';
const GET_PATH = '/get_path';
const GET_README = '/get_readme';
const GET_OBI = '/get_obi';
const GET_DATASET = '/get_all_datasets';
const GET_KEYWORD = '/get_keywords';

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
    else if (this.props.id == 'data_id') {
      this.getData(GET_EDAM_DATA);
    }
    else if (this.props.id == 'topic_id') {
      this.getData(GET_EDAM_TOPIC);
    }
    else if (this.props.id == 'format_id') {
      this.getData(GET_EDAM_FORMAT);
    }
    else if (this.props.id == 'path_id') {
      this.getData(GET_PATH);
    }
    else if (this.props.id == 'readme_file_id') {
      this.getData(GET_README);
    }
    else if (this.props.id == 'assay_id') {
      this.getData(GET_OBI);
    }
    else if (this.props.id == 'parent_dataset_id') {
      this.getData(GET_DATASET);
    }
    else if (this.props.id == 'keyword_id') {
      this.getData(GET_KEYWORD);
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
