import React, { Component } from 'react';
import PropTypes from 'prop-types';
import CurateLayout from '../curateHome/layout';
import fetchData from '../../lib/fetchData';
import OneTrack from './oneTrack';
import { setError } from '../../actions/metaActions';

const GET_DATASET = '/get_dataset_data';

class EditTrack extends Component {
  constructor(props) {
    super(props);
    this.state = {
      tracks: []
    };
  }

  componentDidMount() {
    let url = this.setVariables();
    this.getData(url);
  }

  getData(url) {
    fetchData(url).then( (data) => {
      this.setState({ tracks: data['tracks'] });
    })
    .catch(err => this.props.dispatch(setError(err.error)));
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let format_name = urlList[urlList.length-1];
    return GET_DATASET + '/' + format_name;
  }

  trackSections() {

    if (this.state.tracks.length == 0) {
      return (<strong>No track info associated with this dataset.</strong>);
    }
      
    let sections = this.state.tracks.map((track, i) => {
      return (<OneTrack data={track} index={i} />);
    });
    return sections;
  }
    
  render() {
    return (
      <CurateLayout>
        <h2>Update Dataset Track</h2>
        { this.trackSections() }
      </CurateLayout>
    );
  }

}

EditTrack.propTypes = {
  dispatch: PropTypes.func,
};

export default EditTrack;
