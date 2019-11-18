import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setPhenotype } from '../../actions/phenotypeActions';
import OneAnnotation from './oneAnnotation';
import OneConditionGroup from './oneConditionGroup';
import CommentSection from './commentSection';
const UPDATE_PHENOTYPE = '/phenotype_update';
const DELETE_PHENOTYPE = '/phenotype_delete';
const GET_PHENOTYPE = '/get_phenotype';

const TIMEOUT = 300000;

class EditPhenotype extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleDelete = this.handleDelete.bind(this);
  
    this.state = {
      annotation_id: null,
      group_id: 0,
      isLoading: false,
      isComplete: false,
      gene_count: 0,
      id_to_gene: []
    };
  }

  componentDidMount() {
    let url = this.setVariables();
    this.getData(url);
  }

  handleChange() {
    let currentPheno = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentPheno[key[0]] = key[1];
    }
    this.props.dispatch(setPhenotype(currentPheno));
  }

  handleUpdateOnly(e) {
    e.preventDefault();
    this.handleUpdate(e, '0');
  }
    
  handleUpdateAll(e) {
    e.preventDefault();
    this.handleUpdate(e, '1');
  }

  handleUpdate(e, type) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.phenotype){
      formData.append(key,this.props.phenotype[key]);
    }
    let gene_id_list = this.getGeneIdList();
    formData.append('gene_id_list', gene_id_list);
    formData.append('group_id', this.state.group_id);
    if (type == 1) {
      formData.append('update_all', '1');
    }
    fetchData(UPDATE_PHENOTYPE, {
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

  handleDelete(e, type) {
    e.preventDefault();
    let formData = new FormData();
    let gene_id_list = this.getGeneIdList();
    formData.append('gene_id_list', gene_id_list);
    if (type == 0) {
      formData.append('group_id', this.state.group_id);
    }
    fetchData(DELETE_PHENOTYPE, {
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
          <div className='columns medium-3 small-3'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpdateOnly.bind(this)} > Update annotation for this group of conditions only</button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='submit' id='submit' value='1' className="button expanded" onClick={this.handleUpdateAll.bind(this)} > Update annotation for all groups of conditions</button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to delete this annotation? This DELETION action will be applied to all genes listed and it may not be possible to reverse.')) this.handleDelete(e, 0); }} > Delete annotation for this group of conditions only</button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to delete this annotation along with all groups of conditions associated with it? This DELETION action will be applied to all genes listed and it may not be possible to reverse.')) this.handleDelete(e, 1); }} > Delete annotation for all groups of conditiobs</button>
          </div>
        </div>
      </div>
    );
  }

  getGeneIdList() {
    let gl = document.getElementById('gene_list');
    let gene_id_list = '';
    for (let i = 0; i < gl.options.length; i++) {
      if (gl.options[i].selected) { 
        if (gene_id_list != '') {
          gene_id_list = gene_id_list + ' ';
        }
        gene_id_list = gene_id_list + gl.options[i].value;
      }
    }
    return gene_id_list;
  }

  getData(url) {
    this.setState({ isLoading: true });
    fetchData(url).then( (data) => {
      let currentPheno = {};
      for (let key in data) {
        currentPheno[key] = data[key];
      }
      this.props.dispatch(setPhenotype(currentPheno));
    })
    .catch(err => this.props.dispatch(setError(err.error)))
    .finally(() => this.setState({ isComplete: true, isLoading: false }));
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let id = urlList[urlList.length-1];
    let genesID = 'genes_' + id;
    let annotID = 'annotation_id_' + id;
    let groupID = 'group_id_' + id;
    let gene_list = window.localStorage.getItem(genesID);
    let annotation_id = window.localStorage.getItem(annotID);
    let group_id = window.localStorage.getItem(groupID);
    let url = GET_PHENOTYPE + '/' + annotation_id + '/' + group_id;
    let genes = gene_list.split(' ');
    let gene_count = genes.length;
    let values = genes.map((identifier, index) => {
      let names = identifier.split('|');
      if (gene_count == 1) {
        return <option value={identifier} key={index} selected> {names[0]} </option>;
      }
      else {
        return <option value={identifier} key={index}> {names[0]} </option>;
      }
    });
    this.setState({ id_to_gene: values, 
      gene_list: gene_list, 
      group_id: group_id, 
      gene_count: gene_count 
    });
    return url;
  }

  geneList() {
    return (
      <div className='row'>
        <div className='columns medium-12'>
          <div className='row'>
            <div className='columns medium-12'>
              <label> Choose one or more Genes: (select or unselect multiple genes by pressing the Control (PC) or Command (Mac) key while clicking)
              </label>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-12'>
              <select ref='gene_list' id='gene_list' value={this.props.phenotype.gene_list} onChange={this.handleChange} size={this.state.gene_count} multiple>
                {this.state.id_to_gene}
              </select>
            </div>
          </div>
      </div>
      </div>
    );
  }

  displayForm() {
    return (
      <div>
        <form onSubmit={this.handleUpdate} ref='form'>
          <input name='id' value={this.props.phenotype.id} className="hide" />

          {this.geneList()}

          <OneAnnotation phenotype={this.props.phenotype} onOptionChange={this.handleChange} />

          <OneConditionGroup phenotype={this.props.phenotype} onOptionChange={this.handleChange} />
      
          <CommentSection sec_title='Experiment_comment' name='experiment_comment' value={this.props.phenotype.experiment_comment} onOptionChange={this.handleChange} placeholder='Enter experiment_comment' rows='3' cols='500' />
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

EditPhenotype.propTypes = {
  dispatch: PropTypes.func,
  phenotype: PropTypes.object
};


function mapStateToProps(state) {
  return {
    phenotype: state.phenotype['currentPhenotype']
  };
}

export default connect(mapStateToProps)(EditPhenotype);
