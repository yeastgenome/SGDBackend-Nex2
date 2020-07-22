import React, { Component } from 'react';
import t from 'tcomb-form';
import PropTypes from 'prop-types';
import { setError, setMessage } from '../../actions/metaActions';
import FlexiForm from '../../components/forms/flexiForm';
import { connect } from 'react-redux';

class ReferenceSettings extends Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: false,
      message: '',
      annotations_data: [],
      not_annotations_data: [],
      changeData: {},
      table_primary_key: {
        'Bindingmotifannotation': 'annotation_id',
        'Literatureannotation': 'annotation_id',
      }
    };
  }

  componentDidMount() {
    let id = this.props.match.params.id;
    this.setState({ loading: true, message: '...loading annotations' });
    this._isMounted = true;
    fetch(`/reference_annotations/${id}`, {
      headers: {
        'X-CSRF-Token': window.CSRF_TOKEN
      },
    })
      .then(data => {
        return data.json();
      })
      .then(data => {
        if (this._isMounted) {
          this.setState({ annotations_data: data.annotations, not_annotations_data: data.not_annotations, loading: false });
        }
      })
      .catch(() => {
        this.setState({ loading: false });
      });
  }

  componentWillUnmount() {
    this._isMounted = false;
  }

  handleIndividualFormSubmit(table_name) {
    if(!(table_name in this.state.changeData)  || table_name in this.state.changeData && Object.keys(this.state.changeData[table_name]).length == 0){
      alert('There is nothing to process for this submission.');
    }
    else{
      var message = this.getConfirmationMessage(table_name);
      if (confirm(message)) {
        this.handleProcessing({ [table_name]: this.state.changeData[table_name] });
      }
    }
  }

  handleProcessing(data) {
    let id = this.props.match.params.id;
    this.setState({ loading: true, message: '...Processing' });
    try {
      fetch(`/reference/${id}/transfer_delete_reference_annotations`, {
        headers: {
          'X-CSRF-Token': window.CSRF_TOKEN
        },
        method: 'POST',
        body: JSON.stringify(data)
      })
        .then((response) => {
          if (response.status != 200) {
            return response.json().then((err) => { throw err; });
          }
          return response.json();
        })
        .then((response) => {
          this.setState({ annotations_data: response.annotations, loading: false, message: '',changeData:{} });
          this.props.dispatch(setMessage(response.success));
        })
        .catch(err => {
          this.setState({ loading: false, message: '',changeData:{} });
          this.props.dispatch(setError(err.error));
        });

    } catch (error) {
      this.props.dispatch(setError(error));
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

      Object.keys(data[tableName]).forEach((d,index) => {
        var obj = data[tableName][d];
        if (obj['delete'] == true) {
          message += `${index+1}. annot_id ${obj['id']} will be deleted.
          `;
        }
        else if ('pmid' in obj) {
          message += `${index+1}. annot_id ${obj['id']} will be updated to pmid ${obj['pmid']}.
          `;
        }
      });
    });

    return message;
  }

  handleTransferChange(table_name, e) {
    var primary_key_value = e.target.dataset.primaryIndex;
    var new_pmid_value = e.target.value;

    var chkbox = table_name+'_chkbox_'+primary_key_value;
    document.getElementById(chkbox).checked = false;

    if (table_name in this.state.changeData) {
      var currentStateValue = Object.assign({}, this.state.changeData[table_name]);
      if(new_pmid_value ==  ''){
        delete currentStateValue[primary_key_value];
      }
      else{
        currentStateValue[primary_key_value] = {
          'id': primary_key_value,
          'pmid': new_pmid_value,
        };
      }
      this.setState(() => {
        return {
          changeData: {
            [table_name]: currentStateValue
          }
        };
      });
    }
    else {
      if (new_pmid_value != ''){
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
  }

  handleDeleteChange(table_name, e) {
    var primary_key_value = e.target.dataset.primaryIndex;

    var input = table_name+'_input_'+primary_key_value;
    document.getElementById(input).value = '';

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

  get_headers(table_name, column_names) {
    var headers = column_names.map((item, index) => <td key={`${table_name}_col_${index}`}>{item}</td>);
    headers.push(<td key={`${table_name}_col_${column_names.length + 1}`}>Transfer</td>);
    headers.push(<td key={`${table_name}_col_${column_names.length + 2}`}>Delete</td>);
    return headers;
  }

  get_columns(table_name, table_values) {
    var results = [];
    for (var key in table_values) {
      var value = table_values[key];
      var primary_key = 'annotation_id'; //this.state.table_primary_key[table_name];
      var column_names = Object.keys(value);
      var result = [];
      column_names.forEach((item, index) => {
        result.push(<td key={`${table_name}_col_${index}`}>{value[item]}</td>);
      });
      result.push(<td key={`${table_name}_col_${column_names.length + 1}`}>
        <input id={`${table_name}_input_${value[primary_key]}`} placeholder='Enter PMID' type='number' key={`pmid_${value[primary_key]}`} data-primary-index={value[primary_key]} onChange={(e) => this.handleTransferChange(table_name, e)} /></td>);
      result.push(<td key={`${table_name}_col_${column_names.length + 2}`}>
        <input id={`${table_name}_chkbox_${value[primary_key]}`} type='Checkbox' name='Delete' key={`delete_${value[primary_key]}`} data-primary-index={value[primary_key]} onChange={(e) => this.handleDeleteChange(table_name, e)} /></td>);
      results.push(<tr key={`${table_name}_row_${key}`}>{result}</tr>);
    }
    return results;
  }

  handleDeleteReference() {
    if (confirm('You sure want to delete')) {
      let id = this.props.match.params.id;
      this.setState({ loading: true, message: '...Processing' });
      try {
        fetch(`/reference/${id}/delete_reference`, {
          headers: {
            'X-CSRF-Token': window.CSRF_TOKEN
          },
          method: 'DELETE',
          body: JSON.stringify(this.state.not_annotations_data)
        })
          .then((response) => {
            if (response.status != 200) {
              return response.json().then((err) => { throw err; });
            }
            return response.json();
          })
          .then((response) => {
            this.props.dispatch(setMessage(response.success));
            this.props.history.push('/');
          })
          .catch(err => this.props.dispatch(setError(err.error)));

      } catch (error) {
        this.props.dispatch(setError(error));
      }
    }
  }

  render() {

    if (this.state.loading) {
      return <h3>{this.state.message}</h3>;
    }

    if (this.state.annotations_data.length > 0) {
      return (
        <React.Fragment>
          <h3>Transfer and Delete Reference</h3>

          {
            this.state.annotations_data.map((item, index) => {

              var table_name = Object.keys(item)[0];
              var table_values = item[table_name];
              if (table_values.length == 0) {
                return undefined;
              }
              const fields = this.get_columns(table_name, table_values);

              var value = table_values[0];
              var column_names = Object.keys(value);
              var column_headers = this.get_headers(table_name, column_names);

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
        </React.Fragment>

      );
    }

    if (this.state.not_annotations_data.length > 0) {
      return (
        <React.Fragment>
          <h3>The reference is still linked to following table</h3>
          <p>No annotations are linked to this reference.</p>
          <table>
            <tbody>
              {
                this.state.not_annotations_data.map((item, index) => {
                  var table_name = Object.keys(item)[0];
                  return (<tr key={`${table_name}_${index}`}>
                    <td>{table_name}</td>
                    <td>{item[table_name]}</td>
                  </tr>);
                })
              }
            </tbody>
          </table>
          <button type='button' className='button alert' onClick={() => this.handleDeleteReference()}>Delete Reference</button>
        </React.Fragment>
      );
    }

    return (
      <React.Fragment>
        <h3>This reference is not related to any annotations.</h3>
        <button type='button' className='button alert' onClick={() => this.handleDeleteReference()}>Delete Reference</button>
      </React.Fragment>
    );
  }
}

ReferenceSettings.propTypes = {
  match: PropTypes.object,
  dispatch: PropTypes.func,
  history:PropTypes.any
};

function mapStateToProps(state) {
  return state;
}
// export default ReferenceSettings;
export default connect(mapStateToProps)(ReferenceSettings);