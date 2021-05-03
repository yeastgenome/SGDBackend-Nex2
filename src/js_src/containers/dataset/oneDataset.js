import React, { Component } from 'react';
import PropTypes from 'prop-types';
import AutocompleteSection from '../phenotype/autocompleteSection';

class OneDataset extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.dataset
    };
  }
    
  render() {
	
    return (
      <div>
        {/* format_name, display name */}
        <div className='row'>
          <div className='columns medium-2 small-2'>
            <div> <label> format_name </label> </div>
            <input name='dataset_format_name' value={this.props.dataset.format_name} className="hide" />
            <input type='text' name='format_name' value={this.props.dataset.format_name} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-10 small-10'>
            <div> <label> display_name </label> </div>
            <input type='text' name='display_name' value={this.props.dataset.display_name} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* dbxref_id, dbxref_type, date_public, channel_count & sample_count */}
        <div className='row'>
          <div className='columns medium-3 small-3'>
            <div> <label> dbxref_id </label> </div>
            <input type='text' name='dbxref_id' value={this.props.dataset.dbxref_id} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> dbxref_type </label> </div>
            <input type='text' name='dbxref_type' value={this.props.dataset.dbxref_type} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-3 small-3'>
            <div> <label> date_public </label> </div>
            <input type='text' name='date_public' value={this.props.dataset.date_public} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> channel_count </label> </div>
            <input type='text' name='channel_count' value={this.props.dataset.channel_count} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> sample_count </label> </div>
            <input type='text' name='sample_count' value={this.props.dataset.sample_count} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* is_in_browser etc */}
        <div className='row'>
          <div className='columns medium-2 small-2'>
            <div> <label> is_in_browser </label></div>
            <input type='text' name='is_in_browser' value={this.props.dataset.is_in_browser} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> is_in_spell </label></div>
            <input type='text' name='is_in_spell' value={this.props.dataset.is_in_spell} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-3 small-3'>
            <div> <label> pmids ('|' delimited)</label></div>
            <input type='text' name='pmids' value={this.props.dataset.pmids} onChange={this.props.onOptionChange} />
          </div>
          <div className='columns medium-5 small-5'>
            <div> <label> keyword(s) ('|' delimited)</label> </div>
            <input type='text' name='keywords' value={this.props.dataset.keywords} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* urls */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> dataset url(s) ('|' delimited) </label> </div>
            <input type='text' name='url1' value={this.props.dataset.url1} onChange={this.props.onOptionChange} />
            <input type='text' name='url2' value={this.props.dataset.url2} onChange={this.props.onOptionChange} />
            <input type='text' name='url3' value={this.props.dataset.url3} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* lab */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> lab </label> </div>
            <input type='text' name='lab1' value={this.props.dataset.lab1} onChange={this.props.onOptionChange} />
            <input type='text' name='lab2' value={this.props.dataset.lab2} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* associated file names */} 
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> associated file_name(s) ('|' delimited)</label> </div>
            <input type='text' name='filenames' value={this.props.dataset.filenames} onChange={this.props.onOptionChange} />
          </div>
        </div>

        {/* description */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> description </label> </div>
            <textarea placeholder='Enter description' name='description' value={this.props.dataset.description} onChange={this.props.onOptionChange} rows='4' cols='200' />
          </div>
        </div>
	
        {/* parent_dataset_id */}
        <div className='row'>
          <div className='columns medium-12 small-12'>
            <div> <label> parent_dataset_id (parent dataset format name) </label> </div>
            <AutocompleteSection sec_title='' id='parent_dataset_id' value1='display_name' value2='' selectedIdName='parent_dataset_id' placeholder='Enter EDAM Term' onOptionChange={this.props.onOptionChange} selectedId={this.props.dataset.parent_dataset_id} setNewValue={false} />
          </div>
        </div>

      </div>

    );
  }
}

OneDataset.propTypes = {
  dataset: PropTypes.object,
  onOptionChange: PropTypes.func
};

export default OneDataset;
