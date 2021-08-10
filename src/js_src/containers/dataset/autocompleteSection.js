import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { DataList } from 'react-datalist-field';

class AutocompleteSection extends Component {
  constructor(props) {
    super(props);
  }

  render() {
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
              this.props.options.length > 0?
              <DataList options={this.props.options} id={this.props.id} left={this.props.value1} right={this.props.value2} selectedIdName={this.props.selectedIdName} onOptionChange={this.props.onOptionChange} selectedId={this.props.selectedId} placeholder={this.props.placeholder} setNewValue={this.props.setNewValue} />
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
  options: PropTypes.array,
  value1: PropTypes.string,
  value2: PropTypes.string,
  onOptionChange: PropTypes.func,
  selectedIdName: PropTypes.string,
  selectedId: PropTypes.string,
  placeholder: PropTypes.string,
  setNewValue:PropTypes.bool
};

export default AutocompleteSection;
