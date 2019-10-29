/*eslint-disable */
import React, { Component } from 'react';
import { connect } from 'react-redux';
import t from 'tcomb-form';
import PropTypes from 'prop-types';
import FlexiForm from '../../components/forms/flexiForm';
import Loader from '../../components/loader';
import { setMessage, setError } from '../../actions/metaActions';
import { updateData } from './locusActions';

const DESCRIPTION_LENGTH = 500;
const HEADLINE_LENGTH = 70;
const ALIAS_WARNING_ID = 'sgdAliasWarning';

class LocusBasic extends Component {
  // sidesteps react give some feedback while changing form inputs
  handleChange(data) {
    let description = data['description'];
    if (description.length > DESCRIPTION_LENGTH) {
      this.props.dispatch(setError(`Description cannot be greater than ${DESCRIPTION_LENGTH} characters.`));
    }
    let headline = description.slice(0, HEADLINE_LENGTH);
    headline = headline.slice(0, headline.indexOf(';'));
    let el = document.getElementsByClassName('field-headline')[0];
    el.innerHTML = `<label>Headline</label>${headline}`;
    // manually hide/show warning for 
    for (var i = data.aliases.length - 1; i >= 0; i--) {
      let d = data.aliases[i];
      if (!d) continue;
      let pmids = d.pmids;
      if (!pmids) {
        $(`#${ALIAS_WARNING_ID}`).css('display', 'block');
        return;
      }
    }
    $(`#${ALIAS_WARNING_ID}`).css('display', 'none');
  }

  handleSuccess(data) {
    var headline = data.basic.headline;
    let el = document.getElementsByClassName('field-headline')[0];
    el.innerHTML = `<label>Headline</label>${headline}`;

    this.props.dispatch(updateData(data));
    this.props.dispatch(setMessage('Locus updated.'));
  }

  // dislay a hidden warning about having alias without PMIDS, manually show when there is no PMID for an alias to avoid setting state, re-rendering form
  renderAliasWarning() {
    return (
      <div className='callout warning' id={ALIAS_WARNING_ID} style={{ display: 'none' }}>
        <p><i className='fa fa-exclamation-circle' /> You entered an alias without a PMID</p>
      </div>
    );
  }

  render() {
    let data = this.props.data;
    if (!data || this.props.isPending) return <Loader />;
    let Alias = t.struct({
      alias_id:t.maybe(t.Number),
      alias: t.String,
      pmids: t.maybe(t.String),
      type: t.enums.of([
        'Uniform',
        'Non-uniform',
        'Retired name'
      ], 'Type')
    });
    let Qualifier = t.enums.of([
      'Verified',
      'Uncharacterized',
      'Dubious'
    ], 'Qualifier');
    let bgiSchema = t.struct({
      gene_name_pmids : t.maybe(t.String),
      name_description: t.maybe(t.String),
      name_description_pmids : t.maybe(t.String),
      aliases: t.list(Alias),
      feature_type: t.maybe(t.enums.of(['ARS','LTR retrotransposon','ORF','blocked reading frame','centromere','disabled reading frame','gene group','intein encoding region','long terminal repeat','mating type region', 'matrix attachment site','ncRNA gene','origin of replication','pseudogene','rRNA gene','silent mating type cassette array','snRNA gene','snoRNA gene','tRNA gene','telomerase RNA gene','telomere','transposable element gene'])),
      qualifier: t.maybe(Qualifier),
      description: t.maybe(t.String),
      headline: t.maybe(t.String),
      description_pmids: t.maybe(t.String),
      // ncbi_protein_name: t.maybe(t.String)
    });
    let aliasLayout = locals => {
      return (
        <div className='row'>
          {this.renderAliasWarning()}
          <div className='columns small-2 hide'>{locals.inputs.alias_id}</div>
          <div className='columns small-4'>{locals.inputs.alias}</div>
          <div className='columns small-3'>{locals.inputs.type}</div>
          <div className='columns small-5'>{locals.inputs.pmids}</div>
          <div className='columns small-2'>{locals.inputs.removeItem}</div>
        </div>
      );
    };
    let bgiOptions = {
      fields: {
        description: {
          type: 'textarea',
          label: 'Description'
        },
        feature_type: {
          label: 'Feature type'
        },
        qualifier: {
          label: 'Qualifier'
        },
        headline: {
          label: 'Headline',
          type: 'static'
        },
        name_description: {
          type: 'textarea'
        },
        aliases: {
          disableOrder: true,
          item: {
            template: aliasLayout,
            fields: {
              alias_id:{
                label:'ID'
              },
              pmids: {
                label: 'PMIDS'
              }
            }
          }
        }
      }
    };
    let url = `/locus/${this.props.match.params.id}/basic`;
    return (
      <div className='row'>
        <div className='columns small-12 medium-6'>
          <FlexiForm defaultData={this.props.data.basic} onChange={this.handleChange.bind(this)} onSuccess={this.handleSuccess.bind(this)} requestMethod='PUT' tFormSchema={bgiSchema} tFormOptions={bgiOptions} updateUrl={url} />
        </div>
      </div>
    );
  }
}

LocusBasic.propTypes = {
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

export { LocusBasic as LocusBasic };
export default connect(mapStateToProps)(LocusBasic);
