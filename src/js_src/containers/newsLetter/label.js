import React, { Component } from 'react';

class Label extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <div className="row">
        <div className="columns medium-12">
          <label>{this.props.label}</label>
        </div>
      </div>
    );
  }
}

Label.prototypes={
  label:React.PropTypes.string
};

export default Label;