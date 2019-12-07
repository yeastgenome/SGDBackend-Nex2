import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
// import { connect } from 'react-redux';
// import { Link } from 'react-router-dom';
import { setError } from '../../actions/metaActions';
import { setData } from '../../actions/authorResponseActions';

const GET_DATA = '/author_responses/';
const UPDATE_DATA = '/update_author_response';

const TIMEOUT = 240000;

class ProcessOneResponse extends Component {

  constructor(props) {
    super(props);
    this.onSubmit = this.onSubmit.bind(this);
    this.onChange = this.onChange.bind(this);
    this.state = {
      data: {},
      curation_id: null
    };    
    this.getData();
  }
    
  getData() {
    let urlList = window.location.href.split('/');
    let id = urlList[urlList.length-1];
    let url = GET_DATA + id;
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ data: data, curation_id: id });
    })
    .catch(err => this.props.dispatch(setError(err.error)));
  }

  onSubmit(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.authorResponse){
      formData.append(key,this.props.authorResponse[key]);
    }
    fetchData(UPDATE_DATA, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false
    }).then((data) => {
      this.setState({ isComplete: true, data: data });
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  onChange() {
    let currData = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currData[key[0]] = key[1];
    }
    this.props.dispatch(setData(currData));
  }

  addPaperLink(pmid, reference_id) {
    if (reference_id) {
      return (<div></div>);
    }
    else {
      let addPaperURL = '/#/curate/reference/new';
      return (
        <div className='columns medium-12'>
          <button type='button' className='button expanded' onClick={()=>window.open(addPaperURL, '_blank', 'location=yes,height=600,width=800,scrollbars=yes,status=yes')}> PMID:{pmid} is not in the database. Add this Paper? </button>
        </div>
      );
    }
  }

  checkboxList(data) {
    return (
      <div className='row'>
        <div className='columns medium-4 small-4'>
          Has novel research? <input type="checkbox" name='has_novel_research' value={ data['has_novel_research'] } onChange={this.onChange} />
        </div>
        <div className='columns medium-4 small-4'>
          Has large scale data? <input type="checkbox" name='has_large_scale_data' value={ data['has_large_scale_data'] } onChange={this.onChange} />
        </div>
        <div className='columns medium-4 small-4'>
          Has fast track tag? <input type="checkbox" name='has_fast_track_tag' value={ data['has_fast_track_tag'] } onChange={this.onChange} />
        </div>
        <div className='columns medium-4 small-4'>
          Curator checked datasets? <input type="checkbox" name='curator_checked_datasets' value={ data['curator_checked_datasets'] } onChange={this.onChange} />
        </div>
        <div className='columns medium-4 small-4'>
          Curator checked genelist? <input type="checkbox" name='curator_checked_genelist' value={ data['curator_checked_genelist'] } onChange={this.onChange} />
        </div>
        <div className='columns medium-4 small-4'>
          No action required? <input type="checkbox" name='no_action_required' value={ data['no_action_required'] } onChange={this.onChange} />
        </div>
      </div>
    );									       
  }

  addButtons() {
    let addTagURL = '/#/add_litguide';
    return (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          <button type='submit' id='submit' className="button expanded" onClick={this.onSubmit.bind(this)} > Update AuthorResponse Row </button>
        </div>
        <div className='columns medium-6 small-6'>
          <button type='button' className='button expanded' onClick={()=>window.open(addTagURL, '_blank', 'location=yes,height=600,width=800,scrollbars=yes,status=yes')}> Add curation_tag/topic </button>    
        </div>
      </div>     
    );
  }

  displayData() {
    let data = this.state.data;
    if (data['author_email']) {
      return (
        <form onSubmit={this.onSubmit} ref='form'>
        <div>	    
          <strong>Author Email: </strong> { data['author_email'] } <br></br> 
          <strong>PMID: </strong> { data['pmid'] } <br></br>
          <strong>Research Results: </strong> { data['research_result'] } <br></br>
          <strong>Gene List: </strong> { data['gene_list'] } <br></br>
          <strong>Dataset Description: </strong> { data['dataset_description'] } <br></br>
          <strong>Other Description: </strong> { data['other_description'] } <br></br>
          { this.checkboxList(data) }
          <input type='hidden' name='curation_id' value={this.state.curation_id} />
          <hr></hr>
          { this.addPaperLink(data['pmid'], data['reference_id']) }
          { this.addButtons() }
        </div>
        </form>
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

ProcessOneResponse.propTypes = {
  dispatch: PropTypes.func
};

export default ProcessOneResponse;


