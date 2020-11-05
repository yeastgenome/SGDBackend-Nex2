import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setAllele } from '../../actions/alleleActions';
import OneAllele from './oneAllele';

const ADD_ALLELE = '/allele_add';

class NewAllele extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleResetForm = this.handleResetForm.bind(this);
    
    // this.state = {};
  }

  handleChange() {
    let currentAllele = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentAllele[key[0]] = key[1];
    }
    this.props.dispatch(setAllele(currentAllele));
  }

  handleSubmit(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.allele){
      formData.append(key,this.props.allele[key]);
    }

    fetchData(ADD_ALLELE, {
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

  handleResetForm() {
    let currentAllele = {
      id: 0,
      allele_name: '',
      allele_name_pmids: '',
      affected_gene: '',
      affected_gene_pmids: '',
      so_id: '',
      allele_type_pmids: '',
      description: '',
      description_pmids: ''
    };
    this.props.dispatch(setAllele(currentAllele));
  }

  addButton() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6'>
            <button type='submit' className="button expanded" >Add Allele</button>
          </div>
        </div>
      </div>
    );
  }

  addNote() {

    return (
      <div className='row'>
        <div> <h2> Note: </h2> </div>
        <div>1. Separate PMIDs with space for all PMID(s) fields. eg "32426863 32421706"</div>
        <div>2. For multiple aliases, separate aliases and their corresponding PMIDs with '|'</div>
        <div>Example for multiple aliases: </div>
        <div>Aliases field: "act1-abc-1|act1-abc-2"</div>
        <div>PMID(s) field: "32426863 32421706|32426863" OR "32421706|" OR "|32426863 32421706"</div>
      </div>
    );
  }
    
  render() {

    return (
      <div>
        <form onSubmit={this.handleSubmit} ref='form'>
          <input name='id' value={this.props.allele.id} className="hide" />

          <OneAllele allele={this.props.allele} onOptionChange={this.handleChange} />

          {this.addButton()}

          {this.addNote()}
	
        </form>

      </div>
    );
  }
}

NewAllele.propTypes = {
  dispatch: PropTypes.func,
  allele: PropTypes.object
};


function mapStateToProps(state) {
  return {
    allele: state.allele['currentAllele']
  };
}

export default connect(mapStateToProps)(NewAllele);
