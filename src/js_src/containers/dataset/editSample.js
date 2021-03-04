import React, { Component } from 'react';
import PropTypes from 'prop-types';
import CurateLayout from '../curateHome/layout';
import fetchData from '../../lib/fetchData';
import OneSample from './oneSample';
import { setError } from '../../actions/metaActions';

const GET_DATASET = '/get_dataset_data';

class EditSample extends Component {
  constructor(props) {
    super(props);
    this.state = {
      samples: []
    };
  }

  componentDidMount() {
    let url = this.setVariables();
    this.getData(url);
  }

  getData(url) {
    fetchData(url).then( (data) => {
      this.setState({ samples: data['samples'] });
    })
    .catch(err => this.props.dispatch(setError(err.error)));
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let format_name = urlList[urlList.length-1];
    return GET_DATASET + '/' + format_name;
  }

  sampleSections() {

    if (this.state.samples.length == 0) {
      return (<strong>No sample associated with this dataset.</strong>);
    }
	
    let sections = this.state.samples.map((sample, i) => {
      return (<OneSample data={sample} index={i} />);
    });
    return sections;
  }
    
  render() {
    return (
      <CurateLayout>
        <h2>Update Dataset Sample</h2>
        { this.sampleSections() }
      </CurateLayout>
    );
  }

}

EditSample.propTypes = {
  dispatch: PropTypes.func,
};

export default EditSample;
