import React, { Component } from 'react';
import PropTypes from 'prop-types';
import AutocompleteSection from '../phenotype/autocompleteSection';

class OneMetadata extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.metadata
    };
  }

  render() {
	
    return (
      <div>
        <div><strong>SGDID: {this.props.metadata.sgdid}</strong></div>
        <div><strong><a href={this.props.metadata.s3_url} target='new'>Download this file from s3</a></strong></div>
        <hr />	
        <div className='columns medium-6 small-6'>
          <strong>Search Keywords:</strong> <AutocompleteSection sec_title='' id='keyword_id' value1='display_name' value2='' selectedIdName='Keyword_id' placeholder='Search for keywords' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.keyword_id} setNewValue={false} />
        </div>
        <div className='columns medium-12 small-12'><strong>Update data fields below:</strong></div>

        <hr />
        {/* file display name & previous file name */}
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <div> <label> display_name </label> </div>
            <input type='text' name='display_name' value={this.props.metadata.display_name} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-6 small-6'>
            <div> <label> previous_file_name </label> </div>
            <input type='text' name='previous_file_name' value={this.props.metadata.previous_file_name} onChange={this.props.onOptionChange} />
          </div>
        </div>

	{/* description */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> description </label> </div>
            <textarea placeholder='Enter description' name='description' value={this.props.metadata.description} onChange={this.props.onOptionChange} rows='4' cols='200' />
          </div>
        </div>
	
        {/* file year, date, size, extension & file status */}
        <div className='row'>
          <div className='columns medium-2 small-2'>
            <div> <label> year </label> </div>
            <input type='text' name='year' value={this.props.metadata.year} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-3 small-3'>
            <div> <label> file_date </label> </div>
            <input type='text' name='file_date' value={this.props.metadata.file_date} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-3 small-3'>
            <div> <label> file_size </label> </div>
            <input type='text' name='file_size' value={this.props.metadata.file_size} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> file_extension </label> </div>
            <input type='text' name='file_extension' value={this.props.metadata.file_extension} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> file_status </label> </div>
            <input type='text' name='dbentity_status' value={this.props.metadata.dbentity_status} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* is_in_browser etc */}
        <div className='row'>
          <div className='columns medium-2 small-2'>
            <div> <label> is_in_browser </label></div>
            <input type='text' name='is_in_browser' value={this.props.metadata.is_in_browser} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> is_in_spell </label></div>
            <input type='text' name='is_in_spell' value={this.props.metadata.is_in_spell} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> is_public </label></div>
            <input type='text' name='is_public' value={this.props.metadata.is_public} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-6 small-6'>
            <div> <label> keyword(s) ('|' delimited)</label> </div>
            <input type='text' name='keywords' value={this.props.metadata.keywords} onChange={this.props.onOptionChange} />
          </div>
        </div>
	
        {/* data_id, topic_id, & format_id */}
        <div className='row'>
          <div className='columns medium-4 small-4'>
            <div> <label> data_id (EDAM Term) </label> </div>
            <AutocompleteSection sec_title='' id='data_id' value1='display_name' value2='' selectedIdName='data_id' placeholder='Enter EDAM Term' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.data_id} setNewValue={false} />
          </div>
          <div className='columns medium-4 small-4'>
            <div> <label> topic_id (EDAM Term) </label> </div>
            <AutocompleteSection sec_title='' id='topic_id' value1='display_name' value2='' selectedIdName='topic_id' placeholder='Enter EDAM Term' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.topic_id} setNewValue={false} />
          </div>
          <div className='columns medium-4 small-4'>
            <div> <label> format_id (EDAM Term) </label> </div>
            <AutocompleteSection sec_title='' id='format_id' value1='display_name' value2='' selectedIdName='format_id' placeholder='Enter EDAM Term' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.format_id} setNewValue={false} />
          </div>  
        </div>

        {/* path_id & readme_file_id */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> file_type & pmid(s) ('|' delimited, eg: Dataset:24133141|Supplemental:16690605)</label> </div>
            <input type='text' name='pmids' value={this.props.metadata.pmids} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* path_id & readme_file_id */}
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <div> <label> path_id (file_path) </label> </div>
            <AutocompleteSection sec_title='' id='path_id' value1='display_name' value2='' selectedIdName='path_id' placeholder='Enter file path' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.path_id} setNewValue={true} />
          </div>
          <div className='columns medium-6 small-6'>
            <div> <label> readme_file_id (readme file) </label> </div>
            <AutocompleteSection sec_title='' id='readme_file_id' value1='display_name' value2='' selectedIdName='readme_file_id' placeholder='Enter README file' onOptionChange={this.props.onOptionChange} selectedId={this.props.metadata.readme_file_id} setNewValue={true} />
          </div>
        </div>

      </div>

    );
  }
}

OneMetadata.propTypes = {
  metadata: PropTypes.object,
  onOptionChange: PropTypes.func
};

export default OneMetadata;
