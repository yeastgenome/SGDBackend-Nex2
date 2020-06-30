import React, { Component } from 'react';
import t from 'tcomb-form';
import PropTypes from 'prop-types';

import FlexiForm from '../../components/forms/flexiForm';

class ReferenceSettings extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: {},
      changeData: {},
      table_primary_key: {
        'Bindingmotifannotation': 'annotation_id',
        'Literatureannotation': 'annotation_id',
      }
    };
  }

  componentDidMount() {
    let id = this.props.match.params.id;
    fetch(`/reference_annotations/${id}`, {
      headers: {
        'X-CSRF-Token': window.CSRF_TOKEN
      },
    })
      .then(data => {
        return data.json();
      })
      .then(data => {
        this.setState({ data });
      });
  }

  handleIndividualFormSubmit(table_name) {
    var message = this.getConfirmationMessage(table_name);
    if (confirm(message)) {
      this.handleProcessing({[table_name]:this.state.changeData[table_name]});
    }    
  }

  handleProcessing(data){
    let id = this.props.match.params.id;
    try {
      fetch(`/reference/${id}/delete_reference_annotations`,{
        headers:{
          'X-CSRF-Token': window.CSRF_TOKEN
        },
        method: 'DELETE',
        body:JSON.stringify(data)
      });
    } catch (error) {
      console.error(error);
    }

  }

  getConfirmationMessage(table_name = undefined) {
    var data = '';
    if (table_name == undefined) {
      data = this.state.changeData;
    }
    else {
      data = {
        [table_name]: this.state.changeData[table_name]
      };
    }

    var tables = Object.keys(data);
    var message = '';
    tables.forEach(tableName => {

      message += `
        ${tableName}
      `;

      Object.keys(data[tableName]).forEach((d) => {
        var obj = data[tableName][d];
        if (obj['delete'] == true) {
          message += `
            ${obj['id']} will be delete.
          `;
        }
        else if ('pmid' in obj) {
          message += `
            ${obj['id']}'s reference will be updated to ${obj['pmid']}.
          `;
        }
      });
    });


    return message;
  }



  handleTransferChange(table_name, e) {
    var primary_key_value = e.target.dataset.primaryIndex;
    var new_pmid_value = e.target.value;

    if (table_name in this.state.changeData) {
      var currentStateValue = Object.assign({}, this.state.changeData[table_name]);
      currentStateValue[primary_key_value] = {
        'id': primary_key_value,
        'pmid': new_pmid_value,
      };

      this.setState(() => {
        return {
          changeData: {
            [table_name]: currentStateValue
          }
        };
      });

    }
    else {
      this.setState(() => {
        return {
          changeData: {
            [table_name]: {
              [primary_key_value]:
              {
                'id': primary_key_value,
                'pmid': new_pmid_value,
              },
            }
          }
        };
      });
    }
  }



  handleDeleteChange(table_name, e) {
    var primary_key_value = e.target.dataset.primaryIndex;

    if (table_name in this.state.changeData) {

      var currentStateValue = Object.assign({}, this.state.changeData[table_name]);
      currentStateValue[primary_key_value] = {
        'id': primary_key_value,
        'delete': e.target.checked,
      };

      this.setState(() => {
        return {
          changeData: {
            [table_name]: currentStateValue
          }
        };
      });

    }
    else {
      var checked = e.target.checked;
      this.setState(() => {
        return {
          changeData: {
            [table_name]: {
              [primary_key_value]:
              {
                'id': primary_key_value,
                'delete': checked,
              },
            }
          }
        };
      });
    }
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
          onSuccess={this.handleOnSuccess}
        />
      </div>
    );
  }

  get_headers(column_names) {
    var headers = column_names.map((item) => <td key={item}>{item}</td>);
    headers.push(<td>Transfer</td>);
    headers.push(<td>Delete</td>);
    return headers;
  }

  get_columns(table_name, table_values) {
    var results = [];
    for (var key in table_values) {
      var value = table_values[key];
      var primary_key = this.state.table_primary_key[table_name];
      var column_names = Object.keys(value);
      var result = [];
      column_names.forEach(item => {
        result.push(<td>{value[item]}</td>);
      });
      result.push(<td><input placeholder='Enter PMID' type='number' data-primary-index={value[primary_key]} onChange={(e) => this.handleTransferChange(table_name, e)} /></td>);
      result.push(<td><input type='Checkbox' name='Delete' data-primary-index={value[primary_key]} onChange={(e) => this.handleDeleteChange(table_name, e)} /></td>);
      results.push(<tr>{result}</tr>);
    }
    return results;
  }

  handleSubmit(event) {
    event.preventDefault();
    console.log('handle  submit');
    console.log(event);
  }

  render() {
    var renderData = this.state.data.length > 0 ? true : false;

    return (
      <React.Fragment>
        <h5>Delete Reference</h5>
        {/* {this.renderReferenceSettings()} */}

        {renderData &&

          this.state.data.map((item, index) => {

            var table_name = Object.keys(item)[0];
            var table_values = item[table_name];
            if (table_values.length == 0) {
              return undefined;
            }
            const fields = this.get_columns(table_name, table_values);

            var value = table_values[0];
            var column_names = Object.keys(value);
            var column_headers = this.get_headers(column_names);

            return (
              <div key={table_name}>
                <h4>{table_name}</h4>
                <form id={`form_${table_name.replace(' ', '_').toLowerCase()}`}>
                  <table key={`${table_name}_${index + 1}`}>
                    <thead>
                      <tr key={`${table_name}_${index + 2}`}>
                        {column_headers}
                      </tr>
                    </thead>

                    <tbody key={`${table_name}_${index + 3}`}>
                      {fields}
                    </tbody>
                  </table>
                  <button type='button' className='button' onClick={() => this.handleIndividualFormSubmit(table_name)}>Submit</button>
                  <hr />
                </form>
              </div>
            );
          })
        }

        {
          !renderData && <div>Not related to annotations</div>
        }
      </React.Fragment>

    );
  }
}

ReferenceSettings.propTypes = {
  match: PropTypes.object
};

export default ReferenceSettings;