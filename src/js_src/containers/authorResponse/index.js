import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { setData } from '../../actions/authorResponseActions';
import { connect } from 'react-redux';
// import { setError, setMessage } from '../../actions/metaActions';
import { setError } from '../../actions/metaActions';  
const ADD_DATA = '/add_author_response';

class AuthorResponse extends Component {

  constructor(props) {
    super(props);
    this.onSubmit = this.onSubmit.bind(this);
    this.onChange = this.onChange.bind(this);
    this.onReset = this.onReset.bind(this);
    this.state = { isComplete: false, data: {} };	
  }
 
  onSubmit(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.authorResponse){
      formData.append(key,this.props.authorResponse[key]);
    }
    fetchData(ADD_DATA, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false
    }).then((data) => {
      // this.props.dispatch(setMessage(data.success));
      this.setState({ isComplete: true, data: data });
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  onReset() {
    let currData = {
      pmid: '',
      email: '',
      citation: '',
      has_novel_research: '0',
      has_large_scale_data: '0',
      research_results: '',
      genes: '',
      dateset_desc: '',
      other_desc: ''
    };
    this.props.dispatch(setData(currData));
  }

  onChange() {
    let currData = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currData[key[0]] = key[1];
    }
    this.props.dispatch(setData(currData));
  }

  render() {
    if (this.state.isComplete) {
      return (
        <div><h3>Your response has been sent to SGD curators. Thank you for helping to improve SGD.</h3></div>
      );
    }
    return (
      <form onSubmit={this.onSubmit} ref='form'>
        <div>
          <h3>Information About Your Recently Published Paper</h3>
          <div className='row'>
            <div className='columns small-6'>
              <label>Your email (required)</label>
              <input name='email' value={this.props.authorResponse.email} onChange={this.onChange} type='text' />
            </div>
            <div className='columns small-6'>
              <label>Pubmed ID of your paper (required)</label>
              <input name='pmid' value={this.props.authorResponse.pmid} onChange={this.onChange} type='text' />
            </div>
          </div>
          <label>Citation</label>
          <input name='citation' value={this.props.authorResponse.citation} onChange={this.onChange} type='text' />
          <p>Does this paper contain novel characterizations of the function, role, or localization of a gene product(s)?
          Yes <input type="checkbox" name='has_novel_research' value='1' onChange={this.onChange} /><br></br> 
          If yes, please summarize briefly the novel results.</p>
          <input name='research_result' value={this.props.authorResponse.research_result} onChange={this.onChange} type='text' />
          <p>If this paper focuses on specific genes/proteins, please identify them here (enter a list of gene names/systematic names).</p>
          <input name='genes' value={this.props.authorResponse.genes} onChange={this.onChange} type='text' />
          <p>Does this study include large-scale datasets that you would like to see incorporated into SGD?
          Yes <input type="checkbox" name='has_large_scale_data' value='1' onChange={this.onChange} /><br></br>
          If yes, please describe briefly the type(s) of data.</p>
          <input name='dataset_desc' value={this.props.authorResponse.dataset_desc} onChange={this.onChange} type='text' />
          <p>Is there anything else that you would like us to know about this paper? </p>
          <input name='other_desc' value={this.props.authorResponse.other_desc} onChange={this.onChange} type='text' />
          <div className='row'>
            <div className='columns medium-3 small-3'>
              <button type='submit' className="button expanded">Submit</button>
            </div>
            <div className='columns medium-3 small-3'>
              <button type='reset' className="button expanded" onClick={this.onReset.bind(this)}>Reset</button>
            </div>
          </div>
        </div>
      </form>
    );
  }
}

AuthorResponse.propTypes = {
  dispatch: PropTypes.func,
  authorResponse: PropTypes.object
};


function mapStateToProps(state) {
  return {
    authorResponse: state.authorResponse['currentData']
  };
}

export default connect(mapStateToProps)(AuthorResponse);
