import React, { Component } from 'react';
import PropTypes from 'prop-types';

class CommentSection extends Component {
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
              <label> { this.props.sec_title } </label>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-12'>
      <textarea placeholder={this.props.placeholder} name={this.props.name} value={this.props.value} onChange={this.props.onOptionChange} rows={this.props.rows} cols={this.props.cols} />
            </div>
          </div>
        </div>
      </div>
    );
  }
}

CommentSection.propTypes = {
  sec_title: PropTypes.string,
  name: PropTypes.string,
  value: PropTypes.string,
  onOptionChange: PropTypes.func,
  placeholder: PropTypes.string,
  rows: PropTypes.string,
  cols: PropTypes.string
};

export default CommentSection;
