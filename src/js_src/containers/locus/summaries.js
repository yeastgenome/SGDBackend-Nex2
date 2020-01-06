/* eslint-disable */
import React, { Component } from 'react';
import { connect } from 'react-redux';
import t from 'tcomb-form';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';
import { updateData, setPending, clearPending} from './locusActions';
import { setMessage, setError, clearError } from '../../actions/metaActions';

class LocusSummaries extends Component {
  handleSubmit(e) {
    e.preventDefault();
    let value = this.formInput.getValue();
    if (value) {
      let id = this.props.match.params.id;
      let url = `/locus/${id}/curate`;
      this.props.dispatch(setPending());
      fetchData(url, { type: 'PUT', data: value }).then( (data) => {
        this.props.dispatch(updateData(data));
        this.props.dispatch(setMessage('Locus was updated successfully.'));
        this.props.dispatch(clearError());
        this.props.dispatch(clearPending());
      }).catch( (data) => {
        let errorMessage = data ? data.error : 'There was an error updating the locus.';
        this.props.dispatch(setError(errorMessage));
        this.props.dispatch(clearPending());
        let errorData = this.props.data;
        errorData.paragraphs = value;
        this.props.dispatch(updateData(errorData));
      });
    }
  }

  render() {
    let data = this.props.data;
    
    if (this.props.isPending || !data) return <Loader />;
    
    let FormSchema = t.struct({
      phenotype_summary: t.maybe(t.String),
      regulation_summary: t.maybe(t.String),
      regulation_summary_pmids: t.maybe(t.String),
      protein_summary:t.maybe(t.String),
      sequence_summary:t.maybe(t.String),
      interaction_summary:t.maybe(t.String),
      disease_summary:t.maybe(t.String),
      function_summary:t.maybe(t.String)
    });
    
    let options = {
      fields: {
        phenotype_summary: {
          type: 'textarea'
        },
        regulation_summary: {
          type: 'textarea'
        },
        regulation_summary_pmids: {
          label: 'Regulation summary PMIDs (space-separated)'
        },
        protein_summary:{
          type:'textarea'
        },
        sequence_summary:{
          type:'textarea'
        },
        interaction_summary:{
          type:'textarea'
        },
        disease_summary:{
          type:'textarea'
        },
        function_summary:{
          type:'textarea'
        }
      }
    };

    return (
      <div className='sgd-curate-form row'>
        <div className='columns small-12 medium-6'>
          <form onSubmit={this.handleSubmit.bind(this)}>
            <t.form.Form options={options} ref={input => this.formInput = input} type={FormSchema} value={data.paragraphs} />
            <div className='form-group'>
              <button type='submit' className='button'>Save</button>
            </div>
        </form>
        </div>
      </div>
    );
  }
}

LocusSummaries.propTypes = {
  data: PropTypes.object,
  dispatch: PropTypes.func,
  isPending: PropTypes.bool,
  params: PropTypes.object
};

function mapStateToProps(state) {
  let _data = state.locus.get('data') ? state.locus.get('data').toJS() : null;
  return {

    data: _data,
    isPending: state.locus.get('isPending')
  };
}

export { LocusSummaries as LocusSummaries };
export default connect(mapStateToProps)(LocusSummaries);
