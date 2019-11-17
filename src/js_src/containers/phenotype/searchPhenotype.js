import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setPhenotype } from '../../actions/phenotypeActions';
import TextFieldSection from './textFieldSection';
const GET_PHENOTYPES = '/get_phenotypes/';

const TIMEOUT = 240000;

class SearchPhenotype extends Component {

  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
    this.handleGetAnnotations = this.handleGetAnnotations.bind(this);
    
    this.state = {
      isComplete: false,
      annotations: [],
      isLoading: false
    };    
  }

  handleChange() {
    let currentPheno = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentPheno[key[0]] = key[1];
    }
    this.props.dispatch(setPhenotype(currentPheno));
  }

  handleGetAnnotations(){
    let url = this.setGetUrl();
    this.setState({ annotations: [], isLoading: true });
    fetchData(url, { timeout: TIMEOUT }).then( (data) => {
      this.setState({ annotations: data });
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isLoading: false, isComplete: true }));
  }

  setGetUrl() {
    let genes = this.props.phenotype['genes'];
    let reference = this.props.phenotype['reference'];
    let url = GET_PHENOTYPES;
    if (genes && reference) {
      url = url + genes + '/' + reference;
    }
    else if (genes) {
      url = url + genes + '/None';
    }
    else if (reference) {
      url = url + 'None/' + reference;
    }
    else {
      this.props.dispatch(setMessage('Please enter gene(s) and/or a reference.'));
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

  format_details(details) {
    let conditions = details.split(' | ');
    let rows = conditions.map((c, i) => {
      return ( <tr key={i}><td>{c}</td></tr> );
    });
    return (<table>{rows}</table>);
  }

  getCurateLink(d) {
    let annotation_identifier_list = d.annotation_identifier_list.join(' ');
    return (
      <form method='POST' action='/#/edit_phenotype' target='new'>
        <input type='hidden' name='annotation_id_list' value={annotation_identifier_list} />
        <input type='hidden' name='group_id' value={d.group_id} />
        <input type="submit" value='Curate' />
      </form>
    );
  }

  getAnnotationRows(data) {

    window.localStorage.clear();

    let rows = data.map((d, i) => {
      let identifier_list = d.annotation_identifier_list;
      let genes = [];
      let annotation_id = 0;
      for (let j = 0; j < identifier_list.length; j++) {
        let identifiers = identifier_list[j].split('|');
        genes.push(identifiers[0]);
        if (annotation_id == 0) {
          annotation_id = identifiers[1];
        }
      }
      let gene_list = genes.join(' ');
      let gene_identifier_list = identifier_list.join(' ');
      let details = this.format_details(d.details);
      let min = 1;
      let max = 1000;
      let id =  min + (Math.random() * (max-min));
      let genesID = 'genes_' + id;
      let annotID = 'annotation_id_' + id;
      let groupID = 'group_id_' + id;
      window.localStorage.setItem(genesID, gene_identifier_list);
      window.localStorage.setItem(annotID, annotation_id);
      window.localStorage.setItem(groupID, d.group_id);
      return (
        <tr key={i}>
          <td>{ gene_list }</td>
          <td>{ d.phenotype}</td>
          <td>{ d.experiment_type }</td>
          <td>{ d.mutant_type}</td>
          <td>{ d.strain_background }</td>
          <td>{ details }</td>
          <td>{ d.paper }</td>
          <td><Link to={`/edit_phenotype/${id}`} target='new'><i className='fa fa-edit' /> Curate </Link></td> 
        </tr>
      );
    });
    return rows;
  }


  displayAnnotations() {
    let data = this.state.annotations;
    if (data.length > 0) {
      let rows = this.getAnnotationRows(data);
      return (
        <div>	    
          { this.searchForm() }
          <table>
            <thead>
              <tr>
                <th>Gene(s)</th> 
                <th>Phenotype</th>
                <th>Experiment Type</th>
                <th>Mutant Type</th>
                <th>Strain Background</th>
                <th>Chemicals/Details</th>
                <th>Reference</th>
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
          <div> No phenotype annotations found for your input(s).</div>
        </div>
      );
    }
  }

  searchForm() {
    return (
      <div>
        <form onSubmit={this.handleGetAnnotations} ref='form'>
          <h4>Search annotations by gene name(s) and/or reference:</h4>
          <TextFieldSection sec_title='Gene(s) (SGDID, Systematic Name, eg. YFL039C, S000002429) ("|" delimited)' name='genes' value={this.props.phenotype.genes} onOptionChange={this.handleChange} />
          <TextFieldSection sec_title='Reference (SGDID, PMID, Reference_id, eg. SGD:S000185012, 27650253, reference_id:307729)' name='reference' value={this.props.phenotype.reference} onOptionChange={this.handleChange} />
          {this.addSubmitButton('Search')}    
        </form>
      </div>
    );
  }

  render() {
    if (this.state.isLoading) {
      return (
	<div>
          <div>Please wait while we are retrieving the phenotype annotations from the database.</div>
          <div><Loader /></div>
        </div>
      );
    }
    if (this.state.isComplete) {
      return this.displayAnnotations();
    }
    else {
      return this.searchForm();
    }
  }
}

SearchPhenotype.propTypes = {
  dispatch: PropTypes.func,
  phenotype: PropTypes.object
};


function mapStateToProps(state) {
  return {
    phenotype: state.phenotype['currentPhenotype']
  };
}

export default connect(mapStateToProps)(SearchPhenotype);
