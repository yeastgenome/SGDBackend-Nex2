import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
const GET_STRAINS = '/get_strains';
const GET_EXPERIMENTS = '/get_apo/experiment_type-yeast';
const GET_MUTANTS = '/get_apo/mutant_type';
const GET_QUALIFIERS = '/get_apo/qualifier';
import { setError } from '../../actions/metaActions';

class PulldownSection extends Component {
  constructor(props) {
    super(props);
    this.state = {
      id_to_name: []
    };
  }

  componentDidMount() {
    if (this.props.name == 'taxonomy_id') {
      this.getTaxonomy();
    }
    else if (this.props.name == 'experiment_id') {
      this.getExptType();
    }
    else if (this.props.name == 'mutant_id') {
      this.getMutantType();
    }
    else if (this.props.name == 'qualifier_id') {
      this.getQualifier();
    }
    else {
      this.props.dispatch(setError('Unknown name: ' + this.props.name));
    }
  }
  
  getTaxonomy() {
    fetchData(GET_STRAINS, {
      type: 'GET'
    }).then(data => {
      let values = data['strains'].map((strain, index) => {
        return <option value={strain.taxonomy_id} key={index}> {strain.display_name} </option>;
      });
      this.setState({ id_to_name: [<option value='' key='-1'> -----select strain_background----- </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  getExptType() {
    fetchData(GET_EXPERIMENTS, {
      type: 'GET'
    }).then(data => {
      let types_to_show = [
        '_phenotype assays',
        '___classical genetics',
        '_____heterozygous diploid',
        '_____homozygous diploid',
        '___large-scale survey',
        '_____competitive growth',
        '_______heterozygous diploid, competitive growth',
        '_______homozygous diploid, competitive growth',
        '____heterozygous diploid, large-scale survey',
        '_____homozygous diploid, large-scale survey',
        '____systematic mutation set',
        '______heterozygous diploid, systematic mutation set',
        '______homozygous diploid, systematic mutation set'];

      let values = types_to_show.map((type, index) => {
        let display_name = type.replace(/_/g, '');
        let apo_id = data[display_name];
        return <option value={apo_id} key={index}> {type} </option>;
      });
      this.setState({ id_to_name: values });
    }).catch(err => this.props.dispatch(setError(err.error)));
    
  }

  getMutantType() {
    fetchData(GET_MUTANTS, {
      type: 'GET'
    }).then(data => {
      let values = data.map((mutant, index) => {
        if (mutant.display_name != 'mutant_type') {
          return <option value={mutant.apo_id} key={index}> {mutant.display_name} </option>;
        }
      });
      this.setState({ id_to_name: values });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }  

  getQualifier() {
    fetchData(GET_QUALIFIERS, {
      type: 'GET'
    }).then(data => {
      let values = data.map((qual, index) => {
        if (qual.display_name != 'qualifier') {
          return <option value={qual.apo_id} key={index}> {qual.display_name} </option>;
        }
      });
      this.setState({ id_to_name: [<option value='' key='-1'> -----no selection----- </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  render() {
    return (
      <div className='row'>
        <div className='columns medium-12'>
          <div className='row'>
            <div className='columns medium-12'>
              <label> {this.props.sec_title} </label>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-12'>
              <select value={this.props.value} onChange={this.props.onOptionChange} name={this.props.name}>
                {this.state.id_to_name}
              </select>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

PulldownSection.propTypes = {
  dispatch: PropTypes.func,
  sec_title: PropTypes.string,
  name: PropTypes.string,
  value: PropTypes.string,
  onOptionChange: PropTypes.func
};

export default PulldownSection;
