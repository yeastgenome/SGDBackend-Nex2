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
    this.handleOnSuccess = this.handleOnSuccess.bind(this);
  }
  handleOnSuccess(data) {
    this.setState({ data });
  }

  handleIndividualFormSubmit(table_name){
    console.log(this.state.changeData[table_name]);
  }

  getConfirmationMessage(table_name=undefined){
    // var message = '';
    if (table_name == undefined){
      //All the table and data
    }
    else{
      var data = this.state.changeData[table_name];
      for(var index =0;index<data.length;index++){
        console.log(data[index]);
      } 
    }
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

  handleTransferChange(table_name, e) {
    var primary_key = this.state.table_primary_key[table_name];
    var primary_key_value = e.target.dataset.primaryIndex;
    var new_pmid_value = e.target.value;

    // var textbox = e.target.closest('input');
    // console.log(textbox);
    // textbox.value = '';

    if (table_name in this.state.changeData) {
      // key already in that table
      //have to take care of others

      var currentStateValue = Object.assign({}, this.state.changeData[table_name]);
      currentStateValue[primary_key_value] = {
        [primary_key]: primary_key_value,
        'pmid': new_pmid_value,
      };

      this.setState(() => {
        return {
          changeData: {
            [table_name]: currentStateValue
          }
        };
      },() => console.log(this.state.changeData));

      // if (primary_key_value in this.state.changeData[table_name]){
      //   this.setState(() => {
      //     return {
      //       changeData: {
      //         [table_name]: {
      //           primary_key_value :
      //           {
      //             [primary_key]: primary_key_value,
      //             'delete': e.target.checked,
      //           },
      //         }
      //       }
      //     };
      //   });
      // }
      // //key not in that table
      // else{
      //   this.setState(() => {
      //     return {
      //       changeData: {
      //         [table_name]: {
      //           primary_key_value :
      //           {
      //             [primary_key]: primary_key_value,
      //             'delete': e.target.checked,
      //           },
      //         }
      //       }
      //     };
      //   });
      // }
    }
    else {
      this.setState(() => {
        return {
          changeData: {
            [table_name]: {
              [primary_key_value] :
              {
                [primary_key]: primary_key_value,
                'pmid': new_pmid_value,
              },
            }
          }
        };
      },() => console.log(this.state.changeData));
    }
  }



  handleDeleteChange(table_name, e) {
    var primary_key = this.state.table_primary_key[table_name];
    var primary_key_value = e.target.dataset.primaryIndex;

    // var textbox = e.target.closest('input');
    // console.log(textbox);
    // textbox.value = '';

    if (table_name in this.state.changeData) {
      // key already in that table
      //have to take care of others

      var currentStateValue = Object.assign({}, this.state.changeData[table_name]);
      currentStateValue[primary_key_value] = {
        [primary_key]: primary_key_value,
        'delete': e.target.checked,
      };

      this.setState(() => {
        return {
          changeData: {
            [table_name]: currentStateValue
          }
        };
      },() => console.log(this.state.changeData));

      // if (primary_key_value in this.state.changeData[table_name]){
      //   this.setState(() => {
      //     return {
      //       changeData: {
      //         [table_name]: {
      //           primary_key_value :
      //           {
      //             [primary_key]: primary_key_value,
      //             'delete': e.target.checked,
      //           },
      //         }
      //       }
      //     };
      //   });
      // }
      // //key not in that table
      // else{
      //   this.setState(() => {
      //     return {
      //       changeData: {
      //         [table_name]: {
      //           primary_key_value :
      //           {
      //             [primary_key]: primary_key_value,
      //             'delete': e.target.checked,
      //           },
      //         }
      //       }
      //     };
      //   });
      // }
    }
    else {
      var checked = e.target.checked;
      this.setState(() => {
        return {
          changeData: {
            [table_name]: {
              [primary_key_value] :
              {
                [primary_key]: primary_key_value,
                'delete': checked,
              },
            }
          }
        };
      },() => console.log(this.state.changeData));
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
              //<div key={`${table_name}_${index + 1}`}>{table_name}</div>;
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

        {/* <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(this.state.data,null,2)}</pre> */}
      </React.Fragment>

    );
  }
}

ReferenceSettings.propTypes = {
  match: PropTypes.object
};

export default ReferenceSettings;