import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import PulldownMenu from './pulldownMenu';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setData } from '../../actions/litGuideActions';

const GET_DATA = '/get_papers_by_tag/';

const TIMEOUT = 240000;

class SearchLitGuide extends Component {

  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleGetPapers = this.handleGetPapers.bind(this);
    
    this.state = {
      isComplete: false,
      papers: [],
      isLoading: false
    };    

  }

  handleChange() {
    let currData = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currData[key[0]] = key[1];
    }
    this.props.dispatch(setData(currData));
  }

  handleGetPapers(){
    let url = this.setGetUrl();
    this.setState({ papers: [], isLoading: true });
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ papers: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isLoading: false, isComplete: true }));
  }

  setGetUrl() {
    let tag = this.props.litguide['tag'];
    let gene = this.props.litguide['gene'];
    let year = this.props.litguide['year'];
    if (tag == '--Pick a curation tag--' || tag == '') {
      this.props.dispatch(setMessage('Please pick a tag.'));
    }
    let url = GET_DATA + tag.replace(' ', '_').replace('/', '|');
    if (gene && year) {
      url = url + '/' + gene + '/' + year;
    }
    else if (gene) {
      url = url + '/' + gene + '/None';
    }
    else if (year) {
      url = url + '/None/' + year;
    }
    else {
      url = url + '/None/None';
    }
    return url;
  }

  addSubmitButton(name) {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6'>
            <button type='submit' className="button expanded" > {name} </button>
          </div>
        </div>
      </div>
    );
  }

  getPaperRows(data) {

    window.localStorage.clear();

    let rows = data.map((d, i) => {
      let gene_list_ids = d.gene_list;
      let genes = [];
      for (let j = 0; j < gene_list_ids.length; j++) {
        let identifiers = gene_list_ids[j].split('|');
        genes.push(identifiers[0]);
      }
      let gene_list = genes.join(' ');
      let gene_identifier_list = gene_list_ids.join(' ');
      let min = 1;
      let max = 1000;
      let id =  min + (Math.random() * (max-min));
      let genesID = 'genes_' + id;
      let tagID = 'tag_id_' + id;  
      window.localStorage.setItem(genesID, gene_identifier_list);
      window.localStorage.setItem(tagID, d.pmid + '|' + d.tag + '|' + d.topic + '|' + d.citation);

      return (
        <tr key={i}>
          <td>{ d.citation }</td>
          <td>{ gene_list}</td>
          <td>{ d.pmid }</td>
          <td>{ d.topic }</td>
          <td>{ d.tag }</td>
          <td>{ d.comment }</td>
          <td>{ d.year }</td>
          <td>{ d.date_created }</td>
          <td><Link to={`/edit_litguide/${id}`} target='new'><i className='fa fa-edit' /> Curate </Link></td> 
        </tr>
      );
    });
    return rows;
  }

  displayPapers() {
    let data = this.state.papers;
    if (data.length > 0) {
      let rows = this.getPaperRows(data);
      return (
        <div>	    
          { this.searchForm() }
          <table>
            <thead>
              <tr>
                <th>Citation</th> 
                <th>Gene(s)</th>
                <th>PMID</th>
                <th>Literature topic</th>
                <th>Curation tag</th>
                <th>Curator comment</th>
                <th>Year</th>
                <th>Date created</th>
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
          <div>{ this.searchForm() }</div>
          <div> No papers found for your input(s).</div>
        </div>
      );
    }
  }

  searchForm() {
    return (
      <div>
        <form onSubmit={this.handleGetPapers} ref='form'>

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Search papers by curation tag with or without input gene or year </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <div className='columns small-4'>
                    <div> Pick a curation tag (required): </div>
                    <PulldownMenu name='tag' value={this.props.litguide.tag} onOptionChange={this.handleChange} />
                  </div>
                  <div className='columns small-4'>
                    <div> Pick a year (optional): </div>
                    <PulldownMenu name='year' value={this.props.litguide.year} onOptionChange={this.handleChange} />
                  </div>
                  <div className='columns small-4'>
            <div> Enter a gene (optional, case sensitive): </div>
                    <input type='text' name='gene' value={this.props.litguide.gene} onChange={this.handleChange} />
                  </div>
                </div>
              </div>
            </div>
          </div>
          {this.addSubmitButton('Search')}    
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
	<div>
          <div>Please wait while we are retrieving the relevant papers from the database.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayPapers();
    }
    else {
      return this.searchForm();
    }
  }
}

SearchLitGuide.propTypes = {
  dispatch: PropTypes.func,
  litguide: PropTypes.object
};


function mapStateToProps(state) {
  return {
    litguide: state.litguide['curationData']
  };
}

export default connect(mapStateToProps)(SearchLitGuide);

