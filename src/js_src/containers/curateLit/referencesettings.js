import React, { Component } from 'react';
import t from 'tcomb-form';
import PropTypes from 'prop-types';

import FlexiForm from '../../components/forms/flexiForm';

class ReferenceSettings extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: {}
    };
    this.handleOnSuccess = this.handleOnSuccess.bind(this);
  }
  handleOnSuccess(data) {
    this.setState({ data });
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

  get_columns(table_values) {
    var results = [];
    for (var key in table_values) {
      var value = table_values[key];
      var column_names = Object.keys(value);
      var result = [];
      column_names.forEach(item => {
        result.push(<td>{value[item]}</td>);
      });
      result.push(<td><input  placeholder='Enter PMID' type='number'/></td>);
      result.push(<td><input type='Checkbox' name='Delete' /></td>);
      results.push(<tr>{result}</tr>);
    }
    return results;
  }

  handleSubmit(event){
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
            const data = this.get_columns(table_values);
            
            var value = table_values[0];
            var column_names = Object.keys(value);
            var column_headers = this.get_headers(column_names);

            return (
              <div key={table_name}>
              <h4>{table_name}</h4>
              <form  onSubmit={this.handleSubmit} id={`form_${table_name.replace(' ','_').toLowerCase()}`}>
              <table key={`${table_name}_${index + 1}`}>
                <thead>
                  <tr key={`${table_name}_${index + 2}`}>
                    {column_headers}
                  </tr>
                </thead>

                 <tbody key={`${table_name}_${index+3}`}>
                  {data}
                </tbody>
              </table>
              <button type='submit' className='button'>Submit</button>
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