import React, { Component } from 'react';
import { connect } from 'react-redux';
import fetchData from '../../lib/fetchData';
import { setError, setMessage } from '../../actions/metaActions';
import { setDisease } from '../../actions/diseaseActions';
import { DataList } from 'react-datalist-field';
import Loader from '../../components/loader';
import PropTypes from 'prop-types';
const GET_ECO = '/eco';
const GET_DO = '/do';
const DISEASES = '/disease';
const GET_STRAINS = '/get_strains';
const GET_DISEASES = 'get_diseases';
const ANNOTATION_TYPES = [null, 'computational', 'high-throughput', 'manually curated'];
const SKIP = 5;
const TIMEOUT = 120000;


class DiseaseForm extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleToggleInsertUpdate = this.handleToggleInsertUpdate.bind(this);
    this.handleResetForm = this.handleResetForm.bind(this);
    this.renderActions = this.renderActions.bind(this);
    this.handleGetDiseases = this.handleGetDiseases.bind(this);
    this.handleSelectDisease = this.handleSelectDisease.bind(this);
    this.handleNextPrevious = this.handleNextPrevious.bind(this);
    this.handleDelete = this.handleDelete.bind(this);

    this.state = {
      list_of_eco: [],
      list_of_do: [],
      list_of_taxonomy: [],
      isUpdate: false,
      pageIndex: 0,
      currentIndex: -1,
      list_of_diseases: [],
      isLoading: false
    };

    this.getEco();
    this.getDo();
    this.getTaxonomy();
  }

  getEco() {
    fetchData(GET_ECO, { type: 'GET' })
      .then((data) => {
        this.setState({ list_of_eco: data.success });
      })
      .catch((err) => this.props.dispatch(setError(err.message)));
  }

  getDo() {
    fetchData(GET_DO, { type: 'GET' })
      .then((data) => {
        this.setState({ list_of_do: data.success });
      })
      .catch((err) => this.props.dispatch(setError(err.message)));
  }

  getTaxonomy() {
    fetchData(GET_STRAINS, {
      type: 'GET'
    }).then(data => {
      var values = data['strains'].map((strain, index) => {
        return <option value={strain.taxonomy_id} key={index}> {strain.display_name} </option>;
      });
      this.setState({ list_of_taxonomy: [<option value='' key='-1'> -----select taxonomy----- </option>, ...values] });
    }).catch(err => this.props.dispatch(setError(err.error)));
  }

  handleGetDiseases() {
    this.setState({ list_of_diseases: [], isLoading: true, currentIndex: -1, pageIndex: 0 });
    fetchData(GET_DISEASES, {
      type: 'POST',
      data: {
        dbentity_id: this.props.disease.dbentity_id,
        reference_id: this.props.disease.reference_id
      },
      timeout: TIMEOUT
    })
      .then(data => {
        if (data['success'].length == 0) {
          this.props.dispatch(setMessage('No diseases found for given input.'));
        }
        else {
          this.setState({ list_of_diseases: data['success'] });
          this.handleResetForm();
        }
      })
      .catch(err => this.props.dispatch(setError(err.error)))
      .finally(() => this.setState({ isLoading: false }));
  }

  handleSelectDisease(index) {
    var disease = this.state.list_of_diseases[index];
    var currentDisease = {
      annotation_id: disease['annotation_id'],
      dbentity_id: disease.dbentity_id['id'],
      taxonomy_id: disease.taxonomy_id,
      reference_id: disease.reference_id,
      disease_id: disease.disease_id,
      eco_id: disease.eco_id,
      with_ortholog: disease.with_ortholog,
      annotation_type: disease.annotation_type,
      association_type: disease.association_type,
      date_assigned: disease.date_assigned
    };

    this.props.dispatch(setDisease(currentDisease));
    this.setState({ currentIndex: index });
  }

  handleResetForm() {
    var currentDisease = {
      annotation_id: 0,
      dbentity_id: '',
      taxonomy_id: '',
      reference_id: '',
      eco_id: '',
      disease_id: '',
      with_ortholog: '',
      annotation_type: '',
      association_type: '',
      date_assigned: ''
    };
    this.props.dispatch(setDisease(currentDisease));
  }

  handleToggleInsertUpdate() {
    this.setState((prevState) => {
      return { isUpdate: !prevState.isUpdate, list_of_diseases: [], currentIndex: -1, pageIndex: 0 };
    });
    this.handleResetForm();
  }


  handleNextPrevious(value) {
    this.setState((prevState) => {
      return { pageIndex: prevState.pageIndex + value };
    });
  }

  handleChange() {

    var data = new FormData(this.refs.form);
    var currentDisease = {};
    for (var key of data.entries()) {
      currentDisease[key[0]] = key[1];
    }
    this.props.dispatch(setDisease(currentDisease));
  }

  handleSubmit(e) {
    e.preventDefault();
    this.setState({ isLoading: true });
    fetchData(DISEASES, {
      type: 'POST',
      data: this.props.disease
    })
      .then(data => {
        this.props.dispatch(setMessage(data.success));
        var list_of_diseases = this.state.list_of_diseases;
        list_of_diseases[this.state.currentIndex] = data.disease;
        this.setState({ list_of_diseases: list_of_diseases });
      })
      .catch(err => this.props.dispatch(setError(err.error)))
      .finally(() => this.setState({ isLoading: false }));
  }

  handleDelete(e) {
    e.preventDefault();
    this.setState({ isLoading: true });
    if (this.props.disease.annotation_id > 0) {

      fetchData(`${DISEASES}/${this.props.disease.annotation_id}/${this.props.disease.dbentity_id}`, {
        type: 'DELETE'
      })
        .then((data) => {
          this.props.dispatch(setMessage(data.success));
          var new_list_of_diseases = this.state.list_of_diseases;
          new_list_of_diseases.splice(this.state.currentIndex, 1);
          this.setState({ list_of_diseases: new_list_of_diseases, currentIndex: -1, pageIndex: 0 });
          this.handleResetForm();
        })
        .catch((err) => {
          this.props.dispatch(setError(err.error));
        })
        .finally(() => this.setState({ isLoading: false }));
    }
    else {
      this.setState({ isLoading: false });
      this.props.dispatch(setError('No disease is selected to delete.'));
    }
  }

  renderActions() {
    var pageIndex = this.state.pageIndex;
    var count_of_diseases = this.state.list_of_diseases.length;
    var totalPages = Math.ceil(count_of_diseases / SKIP) - 1;

    if (this.state.isLoading) {
      return (
        <Loader />
      );
    }

    if (this.state.isUpdate) {
      var buttons = this.state.list_of_diseases.filter((i, index) => {
        return index >= (pageIndex * SKIP) && index < (pageIndex * SKIP) + SKIP;
      })
        .map((disease, index) => {
          var new_index = index + pageIndex * SKIP;
          return <li key={new_index} onClick={() => this.handleSelectDisease(new_index)} className={`button medium-only-expanded ${this.state.currentIndex == new_index ? 'success' : ''}`}>{disease.dbentity_id.display_name}</li>;
        }
        );
      return (
        <div>
          <div className='row'>
            <div className='columns medium-12'>
              <div className='expanded button-group'>
                <li type='button' className='button warning' disabled={count_of_diseases < 0 || pageIndex <= 0 ? true : false} onClick={() => this.handleNextPrevious(-1)}> <i className="fa fa-chevron-circle-left"></i> </li>
                {buttons}
                <li type='button' className='button warning' disabled={count_of_diseases == 0 || pageIndex >= totalPages ? true : false} onClick={() => this.handleNextPrevious(1)}> <i className="fa fa-chevron-circle-right"></i></li>
              </div>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-6'>
              <button type='submit' className="button expanded" disabled={this.state.currentIndex > -1 ? '' : 'disabled'}>Update</button>
            </div>
            <div className='columns medium-3'>
              <button type='button' className="button alert expanded" disabled={this.state.currentIndex > -1 ? '' : 'disabled'} onClick={(e) => { if (confirm('Are you sure, you want to delete selected Disease ?')) this.handleDelete(e); }}>Delete</button>
            </div>
          </div>
        </div >

      );
    }
    else {
      return (
        <div className='row'>
          <div className='columns medium-6'>
            <button type='submit' className='button expanded'>Add</button>
          </div>
        </div>
      );
    }
  }

  render() {

    var annotation_types = ANNOTATION_TYPES.map((item) => <option key={item}>{item}</option>);

    return (
      <div>

        <div className='row'>
          <div className='columns medium-6 small-6'>
            <button type="button" className="button expanded" onClick={this.handleToggleInsertUpdate} disabled={!this.state.isUpdate}>Add new disease</button>
          </div>
          <div className='columns medium-6 small-6 end'>
            <button type="button" className="button expanded" onClick={this.handleToggleInsertUpdate} disabled={this.state.isUpdate}>Update existing disease</button>
          </div>
        </div>

        <form ref='form' onSubmit={this.handleSubmit}>

          <input name='annotation_id' className="hide" value={this.props.disease.annotation_id} readOnly />

          {this.state.isUpdate &&
            <ul>
              <li>Filter diseases by target gene,regulator gene or reference</li>
              <li>Click Get database value</li>
              <li>Click on the value to edit</li>
              <li>Edit the field and click update to save</li>
            </ul>
          }

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Gene (sgdid, systematic name) </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <input type='text' name='dbentity_id' onChange={this.handleChange} value={this.props.disease.dbentity_id} />
                </div>
              </div>
            </div>
          </div>


          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Reference (sgdid, pubmed id, reference no) </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <input type='text' name='reference_id' onChange={this.handleChange} value={this.props.disease.reference_id} />
                </div>
              </div>
            </div>
          </div>

          {this.state.isUpdate &&
            <div className='row'>
              <div className='columns medium-12'>
                <div className='row'>
                  <div className='columns medium-6'>
                    <button type='button' className='button expanded' onClick={this.handleGetDiseases}>Get database value</button>
                  </div>
                </div>
              </div>
            </div>
          }


          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Taxonomy </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <select value={this.props.disease.taxonomy_id} onChange={this.handleChange} name='taxonomy_id'>
                    {this.state.list_of_taxonomy}
                  </select>
                </div>
              </div>
            </div>
          </div>


          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Disease DOID </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <DataList options={this.state.list_of_do} id='disease_id' left='display_name' right='format_name' selectedIdName='disease_id' onOptionChange={this.handleChange} selectedId={this.props.disease.disease_id} />
                </div>
              </div>
            </div>
          </div>

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> With Ortholog </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <input type='text' name='with_ortholog' onChange={this.handleChange} value={this.props.disease.with_ortholog} />
                </div>
              </div>
            </div>
          </div>

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Annotation Type </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <select onChange={this.handleChange} name='annotation_type' value={this.props.disease.annotation_type || ''}>
                    {annotation_types}
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Evidence Eco </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <DataList options={this.state.list_of_eco} id='eco_id' left='display_name' right='format_name' selectedIdName='eco_id' onOptionChange={this.handleChange} selectedId={this.props.disease.eco_id} />
                </div>
              </div>
            </div>
          </div>

          {this.renderActions()}

        </form>

      </div>

    );
  }
}

DiseaseForm.propTypes = {
  dispatch: PropTypes.func,
  disease: PropTypes.object
};

function mapStateToProps(state) {

  return {
    disease: state.disease['currentDisease']
  };
}

export default connect(mapStateToProps)(DiseaseForm);
