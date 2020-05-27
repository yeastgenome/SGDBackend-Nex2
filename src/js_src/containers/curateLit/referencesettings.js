import React, { Component } from 'react';
import t from 'tcomb-form';
import PropTypes from 'prop-types';

import FlexiForm from '../../components/forms/flexiForm';

class ReferenceSettings extends Component {
  constructor(props){
    super(props);
    this.state = {
      data: {}
    };
    this.handleOnSuccess = this.handleOnSuccess.bind(this);
  }
  handleOnSuccess(data) {
    this.setState({data});
  }

  renderReferenceSettings() {
    let reasonDelete = [
      'Content not relevant to S. cerevisiae',
      'Duplicate reference',
      'No longer valid record at PubMed',
      'Not a research article',
      'Originally added to database in error',
      'Personal communication no longer needed',
      'Preliminary reference no longer needed',
      'Retraction',
      'Unpublished reference no longer needed'
    ];

    let refSettingsSchema = t.struct({
      reason_deleted: t.enums.of(reasonDelete)
    });
    let ref_id = this.props.match.params.id;
    return (
      <div style={{ maxWidth: '25rem' }}>        
        <FlexiForm
          requestMethod='DELETE' tFormSchema={refSettingsSchema} submitText='Delete'
          updateUrl={`reference/${ref_id}/delete_reference`} confirmRequired
          onSuccess = {this.handleOnSuccess}
        />
        </div>
    );
  }
  render() {
    return (
      <div><h5>Delete Reference</h5>
      {this.renderReferenceSettings()}
      <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(this.state.data,null,2)}</pre>
      </div>

    );
  }
}

ReferenceSettings.propTypes = {
  match: PropTypes.object
};

export default ReferenceSettings;