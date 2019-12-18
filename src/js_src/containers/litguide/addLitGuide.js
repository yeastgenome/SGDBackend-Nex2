import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setData } from '../../actions/litGuideActions';
import PulldownMenu from './pulldownMenu';

const ADD_LITGUIDE = '/literature_guide_add';

const TIMEOUT = 300000;

class AddLitGuide extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    let urlList = window.location.href.split('?');
    if (urlList.length > 1) {
      let pmid = urlList[urlList.length-1];
      let currentData = { 'pmid': pmid };
      this.props.dispatch(setData(currentData));
    }
  }

  handleChange() {
    let currentData = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentData[key[0]] = key[1];
    }
    this.props.dispatch(setData(currentData));
  }

  handleUpdate(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.litguide){
      formData.append(key,this.props.litguide[key]);
    }
    fetchData(ADD_LITGUIDE, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      timeout: TIMEOUT
    }).then((data) => {
      this.props.dispatch(setMessage(data.success));
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  addButtons() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-4 small-4'>
            <button type='submit' id='submit' className="button expanded" onClick={this.handleUpdate.bind(this)} > Add Tag/Topic </button>
          </div>
        </div>
      </div>
    );
  }

  displayForm() {
    return (
      <div>
        <form onSubmit={this.handleUpdate} ref='form'>
          <div className='row'>
            <div className='columns medium-6 small-6'>
              <div> Enter PMID (required): </div>
              <input type='text' name='pmid' value={this.props.litguide.pmid} onChange={this.handleChange} />
            </div>
            <div className='columns medium-6 small-6'>
              <div> Enter one or more genes ('|' delimited) (optional): </div>
              <input type='text' name='genes' value={this.props.litguide.genes} onChange={this.handleChange} />
            </div>
          </div>  
          <div className='row'>
            <div className='columns medium-6 small-6'>
              <div> Curation tag: </div>
              <PulldownMenu name='tag' value={this.props.litguide.tag} onOptionChange={this.handleChange} />
            </div>
            <div className='columns medium-6 small-6'>
              <div> Literature topic: </div>
              <PulldownMenu name='topic' value={this.props.litguide.topic} onOptionChange={this.handleChange} />
            </div>
          </div>

          {this.addButtons()}
        </form>

      </div>
    );
  }

  render() {
    return this.displayForm();
  }
}

AddLitGuide.propTypes = {
  dispatch: PropTypes.func,
  litguide: PropTypes.object
};


function mapStateToProps(state) {
  return {
    litguide: state.litguide['curationData']
  };
}

export default connect(mapStateToProps)(AddLitGuide);
