import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setAllele } from '../../actions/alleleActions';
import { PREVIEW_URL } from '../../constants.js';
import OneAllele from './oneAllele';
const UPDATE_ALLELE = '/allele_update';
const DELETE_ALLELE = '/allele_delete';
const GET_ALLELE = '/get_allele_data';

const TIMEOUT = 300000;

class EditAllele extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleDelete = this.handleDelete.bind(this);
  
    this.state = {
      allele_id: null,
      allele_name: null,
      preview_url: null,	
      isLoading: false,
      isComplete: false,
    };
  }

  componentDidMount() {
    let url = this.setVariables();
    this.getData(url);
  }

  handleChange() {
    let currentAllele = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentAllele[key[0]] = key[1];
    }
    this.props.dispatch(setAllele(currentAllele));
  }

  handleUpdateOnly(e) {
    e.preventDefault();
    this.handleUpdate(e, '0');
  }
    
  handleUpdateAll(e) {
    e.preventDefault();
    this.handleUpdate(e, '1');
  }

  handleUpdate(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.allele){
      formData.append(key,this.props.allele[key]);
    }
    fetchData(UPDATE_ALLELE, {
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

  handleDelete(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.allele){
      formData.append(key,this.props.allele[key]);
    }
    fetchData(DELETE_ALLELE, {
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
          <div className='columns medium-6 small-6'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpdate.bind(this)} > Update Allele data </button>
          </div>
          <div className='columns medium-6 small-6'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to delete this allele along with all the data associated with it?')) this.handleDelete(e); }} > Delete this Allele </button>
          </div>
        </div>
      </div>
    );
  }

  getData(url) {
    this.setState({ isLoading: true });
    fetchData(url).then( (data) => {
      let currentAllele = {};
      for (let key in data) {
        let res = key.match(/pmids/g);
        if (res == 'pmids') {      
          currentAllele[key] = data[key].join(' ');
        }
        else if (key == 'affected_gene') {
          let gene = data[key];
          currentAllele[key] = gene['display_name'];
          currentAllele['affected_gene_pmids'] = gene['pmids'].join(' ');
        }
        else if (key == 'aliases') {
          let aliases = data[key];
          let alias_list = '';
          let pmids = '';
          for (let i = 0; i < aliases.length; i++) {
            let alias = aliases[i];
            if (alias_list != '') {
              alias_list = alias_list + '|';
              pmids = pmids + '|';
            }
            alias_list = alias_list + alias['display_name'];
            pmids = pmids + alias['pmids'].join(' ');
          }
          currentAllele['aliases'] = alias_list;
          currentAllele['alias_pmids'] = pmids;
        }   
        else {
          currentAllele[key] = data[key];
        }
      }
      this.props.dispatch(setAllele(currentAllele));
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isComplete: true, isLoading: false }));
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let allele_name = urlList[urlList.length-1];
    let url = GET_ALLELE + '/' + allele_name;  
    this.setState({
      allele_name: allele_name,
      preview_url: `${PREVIEW_URL}` + '/allele/' + allele_name
    });
    return url;
  }
    
  displayForm() {
    return (
      <div>
        <a href={this.state.preview_url} target='new'>Preview this Allele Page</a>
        <form onSubmit={this.handleUpdate} ref='form'>
          <input name='sgdid' value={this.props.allele.sgdid} className="hide" />
          <OneAllele allele={this.props.allele} onOptionChange={this.handleChange} />
          {this.addButtons()}          	
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
        <div>
          <div>Please wait while we are constructing the update form.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayForm();
    }
    else {
      return (<div>Something is wrong while we are constructing the update form.</div>);
    }
  }
}

EditAllele.propTypes = {
  dispatch: PropTypes.func,
  allele: PropTypes.object
};


function mapStateToProps(state) {
  return {
    allele: state.allele['currentAllele']
  };
}

export default connect(mapStateToProps)(EditAllele);
