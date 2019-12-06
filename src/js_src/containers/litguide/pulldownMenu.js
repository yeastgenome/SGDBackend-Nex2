import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
const GET_TAG = '/get_curation_tag';
const GET_TOPIC = '/get_literature_topic';
const GET_YEAR = '/get_publication_year';

import { setError } from '../../actions/metaActions';

class PulldownMenu extends Component {
  constructor(props) {
    super(props);
    this.state = {
      id_to_name: []
    };
  }

  componentDidMount() {
    if (this.props.name == 'year') {
      this.getYears();
    }
    else if (this.props.name == 'tag') {
      this.getTags();
    }
    else if (this.props.name == 'topic') {
      this.getTopics();
    }
    else {
      this.props.dispatch(setError('Unknown name: ' + this.props.name));
    }
  }
  
  getYears() {
    fetchData(GET_YEAR, {
      type: 'GET'
    }).then(data => {
      var values = data.map((year, index) => {
        return <option value={year} key={index}> {year} </option>;
      });
      this.setState({ id_to_name: [<option value='' key='-1'> Any </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  getTopics() {
    fetchData(GET_TOPIC, {
      type: 'GET'
    }).then(data => {
      var values = data.map((topic, index) => {
        return <option value={topic} key={index}> {topic} </option>;
      });
      this.setState({ id_to_name: [<option value='' key='-1'> --- pick a topic --- </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  getTags() {
    fetchData(GET_TAG, {
      type: 'GET'
    }).then(data => {
      var values = data.map((tag, index) => {
        return <option value={tag} key={index}> {tag} </option>;
      });
      this.setState({ id_to_name: [<option value='' key='-1'> --- pick a tag --- </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  render() {
    return (
      <select value={this.props.value} onChange={this.props.onOptionChange} name={this.props.name}>
        {this.state.id_to_name}
      </select>
    );
  }
}

PulldownMenu.propTypes = {
  dispatch: PropTypes.func,
  name: PropTypes.string,
  value: PropTypes.string,
  onOptionChange: PropTypes.func
};

export default PulldownMenu;
