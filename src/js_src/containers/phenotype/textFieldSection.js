import React, { Component } from 'react';
import PropTypes from 'prop-types';

class TextFieldSection extends Component {
  constructor(props) {
    super(props);
    this.state = {
      // just to have this section in case we need to do something here
      sec_title: props.sec_title
    };
  }

  render() {
    return (
      <div className='row'>
        <div className='columns medium-12'>
          <div className='row'>
            <div className='columns medium-12'>
              <label> { this.state.sec_title } </label>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-12'>
              <input type='text' name={this.props.name} placeholder={this.props.placeholder} value={this.props.value} onChange={this.props.onOptionChange} />
            </div>
          </div>
        </div>
      </div>
    );
  }
}

TextFieldSection.propTypes = {
  sec_title: PropTypes.string,
  name: PropTypes.string,
  value: PropTypes.string,
  onOptionChange: PropTypes.func,
  placeholder: PropTypes.string
};

export default TextFieldSection;
