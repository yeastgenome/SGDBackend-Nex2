import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { DataList } from 'react-datalist-field';
import fetchData from '../../lib/fetchData';
import { setError } from '../../actions/metaActions';
const GET_ASSAYS = '/get_eco';

class ConditionSection extends Component {
  constructor(props) {
    super(props);
    this.state = {
      cond_name: props.class + '_name',
      cond_value: props.class + '_value',
      cond_unit: props.class + '_unit',
      assays: []
    };
  }

  componentDidMount() {  
    if (this.props.isAssay) {
      this.getAssay();
    }
  }

  getAssay() {
    fetchData(GET_ASSAYS, {
      type: 'GET'
    }).then(data => {
      this.setState({ assays: data });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }
 
  temperatureUnits() {
    let degrees = ['--Pick a degree unit--', '°C', '°F'];
    let values = degrees.map((unit, index) => {
      return <option value={unit} key={index}> {unit} </option>;
    });
    return values;
  }

  unitSection() {
    if (this.props.isTemperature) {
      return (
        <div className='columns medium-3 small-3 end'>
          <select name={this.state.cond_unit} onChange={this.props.onOptionChange} value={this.props.unit}> {this.temperatureUnits()} </select>
        </div>
      );
    }
    else {
      return (
        <div className='columns medium-3 small-3 end'>
          <input type='text' name={this.state.cond_unit} placeholder='Enter unit(s)' value={this.props.unit} onChange={this.props.onOptionChange} />
        </div>
      );
    }
  }

  nameSection() {
    if (this.props.isAssay) {
      return (
        <div className='columns medium-5 small-5'>
          <DataList options={this.state.assays} id='assay_name' left='display_name' right='' selectedIdName='assay_name' placeholder='Enter assay name' onOptionChange={this.props.onOptionChange} selectedId={this.props.name} />
        </div>
      );
    }
    else {
      return (	
        <div className='columns medium-5 small-5'>
          <input type='text' name={this.state.cond_name} placeholder='Enter name(s)' value={this.props.name} onChange={this.props.onOptionChange} />
        </div>
      );
    }
  }

  valueSection() {
    return (
      <div className='columns medium-4 small-4'>
        <input type='text' name={this.state.cond_value} placeholder='Enter value(s)' value={this.props.value} onChange={this.props.onOptionChange} />
      </div> 
    );  
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
            { this.nameSection() }
            { this.valueSection() }
            { this.unitSection() }
          </div>
        </div>
      </div>
    );
  }

}

ConditionSection.propTypes = {
  dispatch: PropTypes.func,
  sec_title: PropTypes.string,
  class: PropTypes.string,
  name: PropTypes.string,
  value: PropTypes.string,
  unit: PropTypes.string,
  onOptionChange: PropTypes.func,
  isTemperature: PropTypes.bool,
  isAssay: PropTypes.bool
};

ConditionSection.defaultProps = {
  isTemperature:false,
  isAssay: false
};

export default ConditionSection;

