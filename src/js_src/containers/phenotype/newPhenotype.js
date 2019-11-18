import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setPhenotype } from '../../actions/phenotypeActions';
import TextFieldSection from './textFieldSection';
import OneAnnotation from './oneAnnotation';
import OneConditionGroup from './oneConditionGroup';
import CommentSection from './commentSection';

const ADD_PHENOTYPES = '/phenotype_add';

class NewPhenotype extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.handleResetForm = this.handleResetForm.bind(this);
    
    // this.state = {};
  }

  handleChange() {
    let currentPheno = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentPheno[key[0]] = key[1];
    }
    this.props.dispatch(setPhenotype(currentPheno));
  }

  handleSubmit(e) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.phenotype){
      formData.append(key,this.props.phenotype[key]);
    }

    fetchData(ADD_PHENOTYPES, {
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
    let currentPheno = {
      id: 0,
      gene_list: '',
      reference_id: '',
      taxonomy_id: '',
      experiment_id: '',
      mutant_id: ''
    };
    this.props.dispatch(setPhenotype(currentPheno));
  }

  addButton() {
    return (
      <div>
        <div className='row'>
          <div className='columns medium-6'>
            <button type='submit' className="button expanded" >Add</button>
          </div>
        </div>
      </div>
    );
  }

  render() {

    return (
      <div>
        <form onSubmit={this.handleSubmit} ref='form'>
          <input name='id' value={this.props.phenotype.id} className="hide" />

          <TextFieldSection sec_title='Gene(s) (SGDID, Systematic Name, eg. YFL039C, S000002429) ("|" delimited)' name='gene_list' value={this.props.phenotype.gene_list} onOptionChange={this.handleChange} />

          <OneAnnotation phenotype={this.props.phenotype} onOptionChange={this.handleChange} />

          <OneConditionGroup phenotype={this.props.phenotype} onOptionChange={this.handleChange} />
      
          <CommentSection sec_title='Experiment_comment' name='experiment_comment' value={this.props.phenotype.experiment_comment} onOptionChange={this.handleChange} placeholder='Enter experiment_comment' rows='3' cols='500' />

          {this.addButton()}

        </form>

      </div>
    );
  }
}

NewPhenotype.propTypes = {
  dispatch: PropTypes.func,
  phenotype: PropTypes.object
};


function mapStateToProps(state) {
  return {
    phenotype: state.phenotype['currentPhenotype']
  };
}

export default connect(mapStateToProps)(NewPhenotype);
