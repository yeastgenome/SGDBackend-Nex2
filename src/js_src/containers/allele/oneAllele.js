import React, { Component } from 'react';
import PropTypes from 'prop-types';
import TwoColTextField from './twoColTextField';
import AutocompleteSection from '../phenotype/autocompleteSection';

class OneAllele extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.allele
    };
  }

  render() {
	
    return (

      <div>
	
        {/* allele name & references */}
        <TwoColTextField sec_title='Allele name' name='allele_name' value={this.props.allele.allele_name} onOptionChange={this.props.onOptionChange} sec_title2='PMID(s) for allele name (optional)' name2='allele_name_pmids' value2={this.props.allele.allele_name_pmids} onOptionChange2={this.props.onOptionChange} />

        {/* affected gene name & references */}
        <TwoColTextField sec_title='Affected gene (sgdid, systematic name)' name='affected_gene' value={this.props.allele.affected_gene} onOptionChange={this.props.onOptionChange} sec_title2='PMID(s) for affected gene (optional)' name2='affected_gene_pmids' value2={this.props.allele.affected_gene_pmids} onOptionChange2={this.props.onOptionChange} />
	
        {/* alias names & references */}
        <TwoColTextField sec_title='Alias names ("|" delimited)' name='aliases' value={this.props.allele.aliases} onOptionChange={this.props.onOptionChange} sec_title2='PMID(s) for aliases (optional, "|" delimited)' name2='alias_pmids' value2={this.props.allele.alias_pmids} onOptionChange2={this.props.onOptionChange} />
        
        {/* Allele type & references */}
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <div> <label> Allele type </label> </div>
            <AutocompleteSection sec_title='' id='so_id' value1='display_name' value2='' selectedIdName='so_id' placeholder='Enter allele type' onOptionChange={this.props.onOptionChange} selectedId={this.props.allele.so_id} setNewValue={false} /> 
          </div>
          <div className='columns medium-6 small-6'>
            <div> <label> PMID(s) for allele type (optional) </label> </div>
            <input type='text' name='allele_type_pmids' value={this.props.allele.allele_type_pmids} onChange={this.props.onOptionChange} />
          </div>
        </div>
	
	
        {/* desctription & references */}
        <div className='row'>
          <div className='columns medium-6 small-6'>
            <div> <label> Allele Description </label> </div>
            <textarea placeholder='Enter description' name='description' value={this.props.allele.description} onChange={this.props.onOptionChange} rows='4' cols='200' />
          </div>
          <div className='columns medium-6 small-6'>
            <div> <label> PMID(s) for description (optional) </label> </div>
            <input type='text' name='description_pmids' value={this.props.allele.description_pmids} onChange={this.props.onOptionChange} />
          </div>
        </div>
	
      </div>

    );
  }
}

OneAllele.propTypes = {
  allele: PropTypes.object,
  onOptionChange: PropTypes.func
};

export default OneAllele;
