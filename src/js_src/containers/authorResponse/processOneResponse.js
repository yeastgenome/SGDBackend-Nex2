import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setMessage, setError } from '../../actions/metaActions';
import { setData } from '../../actions/authorResponseActions';

const GET_DATA = '/author_responses/';
const UPDATE_DATA = '/edit_author_response';

const TIMEOUT = 240000;

class ProcessOneResponse extends Component {

  constructor(props) {
    super(props);
    this.onSubmit = this.onSubmit.bind(this);
    this.onChange = this.onChange.bind(this);
    this.onChange4tag = this.onChange4tag.bind(this);
    this.onChange4datasets = this.onChange4datasets.bind(this);
    this.onChange4genelist = this.onChange4genelist.bind(this);
    this.onChange4action = this.onChange4action.bind(this);
    this.state = {
      data: {},
      curation_id: null,
      has_fast_track_tag: '0',
      curator_checked_datasets: '0',
      curator_checked_genelist: '0',
      no_action_required: '0'
    };    
    this.getData();
  }
    
  getData() {
    let urlList = window.location.href.split('/');
    let id = urlList[urlList.length-1];
    let url = GET_DATA + id;
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ data: data, 
        curation_id: id, 
        has_fast_track_tag: data['has_fast_track_tag'],
        curator_checked_datasets: data['curator_checked_datasets'],
        curator_checked_genelist: data['curator_checked_genelist'],
        no_action_required: data['no_action_required']
      });
    })
    .catch(err => this.props.dispatch(setError(err.error)));
  }

  onSubmit(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.authorResponse){
      formData.append(key,this.props.authorResponse[key]);
    }
    formData.append('curation_id', this.state.curation_id);
    fetchData(UPDATE_DATA, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false
    }).then((data) => {
      this.props.dispatch(setMessage(data.success));
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  onChange4tag() {
    this.setState(prevState=>({ 
      has_fast_track_tag: !prevState.has_fast_track_tag 
    }));
    this.onChange();
  }

  onChange4datasets() {
    this.setState(prevState=>({
      curator_checked_datasets: !prevState.curator_checked_datasets 
    }));
    this.onChange();
  }

  onChange4genelist() {
    this.setState(prevState=>({
      curator_checked_genelist: !prevState.curator_checked_genelist 
    }));
    this.onChange();
  }

  onChange4action() {
    this.setState(prevState=>({
      no_action_required: !prevState.no_action_required 
    }));
    this.onChange();
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

  checkboxList() {
    return (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          Has fast track tag? <input type="checkbox" name='has_fast_track_tag' value={this.state.has_fast_track_tag} checked={this.state.has_fast_track_tag} onChange={this.onChange4tag} />
        </div>
        <div className='columns medium-6 small-6'>
          Curator checked datasets? <input type="checkbox" name='curator_checked_datasets' value={this.state.curator_checked_datasets} checked={this.state.curator_checked_datasets} onChange={this.onChange4datasets} />
        </div>
        <div className='columns medium-6 small-6'>
          Curator checked genelist? <input type="checkbox" name='curator_checked_genelist' value={this.state.curator_checked_genelist} checked={this.state.curator_checked_genelist} onChange={this.onChange4genelist} />
        </div>
        <div className='columns medium-6 small-6'>
          No action required? <input type="checkbox" name='no_action_required' value={this.state.no_action_required} checked={this.state.no_action_required} onChange={this.onChange4action} />
        </div>
      </div>
    );									       
  }

  addButtons() {
    let data = this.state.data;
    let addTagURL = '/#/add_litguide?' + data['pmid'];
    return (
      <div className='row'>
        <div className='columns medium-6 small-6'>
          <button type='submit' className="button expanded"> Update AuthorResponse Row </button>
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
          <strong>Has novel research? </strong> { (data['has_novel_research'])? 'Yes':'No' } <br></br>
          <strong>Has large scale data? </strong>{ (data['has_large_scale_data'])? 'Yes':'No' } <br></br>
          <strong>Date created: </strong>{ data['date_created'] } <br></br>
          { this.checkboxList() }
          <input type='hidden' name='curation_id' value={data['curation_id']} />
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
  dispatch: PropTypes.func,
  authorResponse: PropTypes.object
};

function mapStateToProps(state) {
  return {
    authorResponse: state.authorResponse['currentData']
  };
}

export default connect(mapStateToProps)(ProcessOneResponse);



