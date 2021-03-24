import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import LoadDATASET from './loadDataset';

class LoadDataset extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <CurateLayout>
        <h1>Load Dataset/Sample(s)</h1>
        <LoadDATASET />
      </CurateLayout>
    );
  }

}

export default LoadDataset;
