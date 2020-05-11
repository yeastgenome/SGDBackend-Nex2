import React, { Component } from 'react';
import t from 'tcomb-form';

import FlexiForm from '../../components/forms/flexiForm';

class ReferenceSettings extends Component {
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

    let ref_id = this.props.params.id;
    return (
      <div style={{ maxWidth: '25rem' }}>
        <FlexiForm
          requestMethod='POST' tFormSchema={refSettingsSchema} submitText='Delete'
          updateUrl={`reference/${ref_id}/delete_reference`} confirmRequired
        />
        </div>
    );
  }
  render() {
    return (
      <div><h5>Delete Reference</h5>
      {this.renderReferenceSettings()}
      </div>

    );
  }
}

ReferenceSettings.propTypes = {
  params: React.PropTypes.object
};

export default ReferenceSettings;