import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import ProcessOneResponse from './processOneResponse';

class ProcessOne extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
          <h1>Author Responses</h1>
          <ProcessOneResponse />
      </CurateLayout>
    );
  }

}

export default ProcessOne;
