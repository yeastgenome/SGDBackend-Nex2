import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { Link } from 'react-router-dom';
import { setError } from '../../actions/metaActions';

const GET_DATA = '/author_responses';

const TIMEOUT = 240000;

class ShowAllResponses extends Component {

  constructor(props) {
    super(props);

    this.state = {
      data: []
    };    

    this.getData();
  }

  getData() {
    fetchData(GET_DATA, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ data: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)));
  }

  getDataRows(data) {
    let rows = data.map((d, i) => {
      let id = d.curation_id;
      return (
        <tr key={i}>
          <td>{ d.author_email }</td>
          <td>{ d.pmid }</td>
          <td>{ d.research_results }</td>
          <td>{ d.gene_list }</td>
          <td>{ d.dataset_description }</td>
          <td>{ d.other_description }</td>
          <td>{ d.date_created }</td>
          <td><Link to={`/author_responses/${id}`} target='new'><i className='fa fa-edit' /> Curate </Link></td> 
        </tr>
      );
    });
    return rows;
  }

  displayData() {
    let data = this.state.data;
    if (data.length > 0) {
      let rows = this.getDataRows(data);
      return (
        <div>	    
          <table>
            <thead>
              <tr>
                <th>author email</th> 
                <th>pmid</th>
                <th>research results</th>
                <th>gene list</th>
                <th>dataset description</th>
                <th>other description</th>
                <th>date created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              { rows }
            </tbody>
          </table>
        </div>
      );
    }
    else {
      return (
        <div>
          <div> No new author response data found. </div>
        </div>
      );
    }
  }

  render() {
    return this.displayData();
  }
}

ShowAllResponses.propTypes = {
  dispatch: PropTypes.func
};

export default ShowAllResponses;

