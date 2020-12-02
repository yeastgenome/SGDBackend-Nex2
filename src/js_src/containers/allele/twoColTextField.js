import React, { Component } from 'react';
import PropTypes from 'prop-types';

class TwoColTextField extends Component {
  constructor(props) {
    super(props);
    this.state = {
      // just to have this section in case we need to do something here
      sec_title: props.sec_title,
      sec_title2: props.sec_title2
    };
  }

  render() {
    return (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          <div> <label> { this.state.sec_title } </label> </div>
          <input type='text' name={this.props.name} value={this.props.value} onChange={this.props.onOptionChange} />
        </div>
        <div className='columns medium-6 small-6'>
          <div> <label> { this.state.sec_title2 } </label> </div>
          <input type='text' name={this.props.name2} value={this.props.value2} onChange={this.props.onOptionChange} />
        </div>
      </div>
    );
  }
}

TwoColTextField.propTypes = {
  sec_title: PropTypes.string,
  name: PropTypes.string,
  value: PropTypes.string,
  onOptionChange: PropTypes.func,
  sec_title2: PropTypes.string,
  name2: PropTypes.string,
  value2: PropTypes.string,
};

export default TwoColTextField;
