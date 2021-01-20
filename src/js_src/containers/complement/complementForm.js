import React, { Component } from 'react';
import { connect } from 'react-redux';
import fetchData from '../../lib/fetchData';
import { setError, setMessage } from '../../actions/metaActions';
import { setComplement } from '../../actions/complementActions';
import { DataList } from 'react-datalist-field';
import Loader from '../../components/loader';
import PropTypes from 'prop-types';
const GET_ECO = '/eco';
const GET_RO = '/ro';
const COMPLEMENTS = '/complement';
const GET_STRAINS = '/get_strains';
const GET_COMPLEMENTS = 'get_complements';
const DIRECTION_TYPES = [null, 'yeast complements other', 'other complements yeast'];
const SKIP = 5;
const TIMEOUT = 120000;


class ComplementForm extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleToggleInsertUpdate = this.handleToggleInsertUpdate.bind(this);
    this.handleResetForm = this.handleResetForm.bind(this);
    this.renderActions = this.renderActions.bind(this);
    this.handleGetComplements = this.handleGetComplements.bind(this);
    this.handleSelectComplement = this.handleSelectComplement.bind(this);
    this.handleNextPrevious = this.handleNextPrevious.bind(this);
    this.handleDelete = this.handleDelete.bind(this);

    this.state = {
      list_of_eco: [],
      list_of_ro: [],
      list_of_taxonomy: [],
      isUpdate: false,
      pageIndex: 0,
      currentIndex: -1,
      list_of_complements: [],
      isLoading: false
    };

    this.getEco();
    this.getRo();
    this.getTaxonomy();
  }

  getEco() {
    fetchData(GET_ECO, { type: 'GET' })
      .then((data) => {
        this.setState({ list_of_eco: data.success });
      })
      .catch((err) => this.props.dispatch(setError(err.message)));
  }

  getRo() {
    fetchData(GET_RO, { type: 'GET' })
      .then((data) => {
        this.setState({ list_of_ro: data.success });
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

  handleGetComplements() {
    this.setState({ list_of_complements: [], isLoading: true, currentIndex: -1, pageIndex: 0 });
    fetchData(GET_COMPLEMENTS, {
      type: 'POST',
      data: {
        dbentity_id: this.props.complement.dbentity_id,
        reference_id: this.props.complement.reference_id
      },
      timeout: TIMEOUT
    })
      .then(data => {
        if (data['success'].length == 0) {
          this.props.dispatch(setMessage('No functional complements found for given input.'));
        }
        else {
          this.setState({ list_of_complements: data['success'] });
          this.handleResetForm();
        }
      })
      .catch(err => this.props.dispatch(setError(err.error)))
      .finally(() => this.setState({ isLoading: false }));
  }

  handleSelectComplement(index) {
    var complement = this.state.list_of_complements[index];
    var currentComplement = {
      annotation_id: complement['annotation_id'],
      dbentity_id: complement.dbentity_id['id'],
      taxonomy_id: complement.taxonomy_id,
      reference_id: complement.reference_id,
      eco_id: complement.eco_id,
      ro_id: complement.ro_id,
      dbxref_id: complement.dbxref_id,
      direction: complement.direction,
      obj_url: complement.obj_url,
      curator_comment: complement.curator_comment,
      source_id: complement.source_id,
      date_assigned: complement.date_assigned
    };
    this.props.dispatch(setComplement(currentComplement));
    this.setState({ currentIndex: index });
  }

  handleResetForm() {
    var currentComplement = {
      annotation_id: 0,
      dbentity_id: '',
      taxonomy_id: '',
      reference_id: '',
      eco_id: '',
      ro_id: '',
      dbxref_id: '',
      source_id: '',
      direction: '',
      obj_url: '',
      curator_comment: '',
      date_created: ''
    };
    this.props.dispatch(setComplement(currentComplement));
  }

  handleToggleInsertUpdate() {
    this.setState((prevState) => {
      return { isUpdate: !prevState.isUpdate, list_of_complements: [], currentIndex: -1, pageIndex: 0 };
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
    var currentComplement = {};
    for (var key of data.entries()) {
      currentComplement[key[0]] = key[1];
    }
    this.props.dispatch(setComplement(currentComplement));
  }

  handleSubmit(e) {
    e.preventDefault();
    this.setState({ isLoading: true });
    fetchData(COMPLEMENTS, {
      type: 'POST',
      data: this.props.complement
    })
      .then(data => {
        this.props.dispatch(setMessage(data.success));
        var list_of_complements = this.state.list_of_complements;
        list_of_complements[this.state.currentIndex] = data.complement;
        this.setState({ list_of_complements: list_of_complements });
      })
      .catch(err => this.props.dispatch(setError(err.error)))
      .finally(() => this.setState({ isLoading: false }));
  }

  handleDelete(e) {
    e.preventDefault();
    this.setState({ isLoading: true });
    if (this.props.complement.annotation_id > 0) {
      fetchData(`${COMPLEMENTS}/${this.props.complement.annotation_id}/${this.props.complement.dbentity_id}`, {type: 'DELETE'})
        .then((data) => {
          this.props.dispatch(setMessage(data.success));
          var new_list_of_complements = this.state.list_of_complements;
          new_list_of_complements.splice(this.state.currentIndex, 1);
          this.setState({ list_of_complements: new_list_of_complements, currentIndex: -1, pageIndex: 0 });
          this.handleResetForm();
        })
        .catch((err) => {
          this.props.dispatch(setError(err.error));
        })
        .finally(() => this.setState({ isLoading: false }));
    }
    else {
      this.setState({ isLoading: false });
      this.props.dispatch(setError('No functional complement is selected to delete.'));
    }
  }

  renderActions() {
    var pageIndex = this.state.pageIndex;
    var count_of_complements = this.state.list_of_complements.length;
    var totalPages = Math.ceil(count_of_complements / SKIP) - 1;

    if (this.state.isLoading) {
      return (
        <Loader />
      );
    }

    if (this.state.isUpdate) {
      var buttons = this.state.list_of_complements.filter((i, index) => {
        return index >= (pageIndex * SKIP) && index < (pageIndex * SKIP) + SKIP;
      })
        .map((complement, index) => {
          var new_index = index + pageIndex * SKIP;
          return <li key={new_index} onClick={() => this.handleSelectComplement(new_index)} className={`button medium-only-expanded ${this.state.currentIndex == new_index ? 'success' : ''}`}>{complement.dbentity_id.display_name}</li>;
        }
        );
      return (
        <div>
          <div className='row'>
            <div className='columns medium-12'>
              <div className='expanded button-group'>
                <li type='button' className='button warning' disabled={count_of_complements < 0 || pageIndex <= 0 ? true : false} onClick={() => this.handleNextPrevious(-1)}> <i className="fa fa-chevron-circle-left"></i> </li>
                {buttons}
                <li type='button' className='button warning' disabled={count_of_complements == 0 || pageIndex >= totalPages ? true : false} onClick={() => this.handleNextPrevious(1)}> <i className="fa fa-chevron-circle-right"></i></li>
              </div>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-6'>
              <button type='submit' className="button expanded" disabled={this.state.currentIndex > -1 ? '' : 'disabled'}>Update</button>
            </div>
            <div className='columns medium-3'>
              <button type='button' className="button alert expanded" disabled={this.state.currentIndex > -1 ? '' : 'disabled'} onClick={(e) => { if (confirm('Are you sure, you want to delete selected Complement ?')) this.handleDelete(e); }}>Delete</button>
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

    var direction_types = DIRECTION_TYPES.map((item) => <option key={item}>{item}</option>);
    return (
      <div>

        <div className='row'>
          <div className='columns medium-6 small-6'>
            <button type="button" className="button expanded" onClick={this.handleToggleInsertUpdate} disabled={!this.state.isUpdate}>Add new functional complement</button>
          </div>
          <div className='columns medium-6 small-6 end'>
            <button type="button" className="button expanded" onClick={this.handleToggleInsertUpdate} disabled={this.state.isUpdate}>Update existing functional complement</button>
          </div>
        </div>

        <form ref='form' onSubmit={this.handleSubmit}>

          <input name='annotation_id' className="hide" value={this.props.complement.annotation_id} readOnly />

          {this.state.isUpdate &&
            <ul>
              <li>Filter complements by target gene or reference</li>
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
                  <input type='text' name='dbentity_id' onChange={this.handleChange} value={this.props.complement.dbentity_id} />
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
                  <input type='text' name='reference_id' onChange={this.handleChange} value={this.props.complement.reference_id} />
                </div>
              </div>
            </div>
          </div>

          {this.state.isUpdate &&
            <div className='row'>
              <div className='columns medium-12'>
                <div className='row'>
                  <div className='columns medium-6'>
                    <button type='button' className='button expanded' onClick={this.handleGetComplements}>Get database value</button>
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
                  <select value={this.props.complement.taxonomy_id} onChange={this.handleChange} name='taxonomy_id'>
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
                                <label> Evidence Eco </label>
                            </div>
                        </div>
                        <div className='row'>
                            <div className='columns medium-12'>
                                <DataList options={this.state.list_of_eco} id='eco_id' left='display_name' right='format_name' selectedIdName='eco_id' onOptionChange={this.handleChange} selectedId={this.props.complement.eco_id} />
                            </div>
                        </div>
                    </div>
          
          </div>
                
          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> ROID </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <DataList options={this.state.list_of_ro} id='ro_id' left='display_name' right='format_name' selectedIdName='ro_id' onOptionChange={this.handleChange} selectedId={this.props.complement.ro_id} />
                </div>
              </div>
            </div>
          </div>

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Human gene HGNC ID </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <input type='text' name='dbxref_id' onChange={this.handleChange} value={this.props.complement.dbxref_id} />
                </div>
              </div>
            </div>
          </div>
                
         <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                    <label> Comments </label>
                </div>
                </div>
                <div className='row'>
                    <div className='columns medium-12'>
                        <input type='text' name='curator_comment' onChange={this.handleChange} value={this.props.complement.curator_comment} />
                    </div>
                </div>
                </div>
         </div>         

          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <label> Direction of complementation </label>
                </div>
              </div>
              <div className='row'>
                <div className='columns medium-12'>
                  <select onChange={this.handleChange} name='direction' value={this.props.complement.direction || ''}>
                    {direction_types}
                  </select>
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

ComplementForm.propTypes = {
  dispatch: PropTypes.func,
  complement: PropTypes.object
};

function mapStateToProps(state) {

  return {
    complement: state.complement['currentComplement']
  };
    
}

export default connect(mapStateToProps)(ComplementForm);