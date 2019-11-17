import React, { Component } from 'react';
import PropTypes from 'prop-types';

import AutocompleteSection from './autocompleteSection';
import CommentSection from './commentSection';
import PulldownSection from './pulldownSection';
import TextFieldSection from './textFieldSection';

class OneAnnotation extends Component {
  constructor(props) {
    super(props);

    this.state = {
      // use data to set data for updating one phenotype annotation
      data: this.props.phenotype
    };
  }

  render() {
    return (
      <div>
        {/* reference */}
        <TextFieldSection sec_title='Reference (SGDID, PMID, Reference_id, eg. SGD:S000185012, 27650253, reference_id:307729)' name='reference_id' value={this.props.phenotype.reference_id} onOptionChange={this.props.onOptionChange} />

        {/* Experiment_type */}
        <PulldownSection sec_title='Experiment_type' name='experiment_id' value={this.props.phenotype.experiment_id} onOptionChange={this.props.onOptionChange} />

        {/* Mutant_type */}
        <PulldownSection sec_title='Mutant_type' name='mutant_id' value={this.props.phenotype.mutant_id} onOptionChange={this.props.onOptionChange} />

        {/* Observable */}
        <AutocompleteSection sec_title='Observable' id='observable_id' value1='display_name' value2='format_name' placeholder='Enter observable' selectedIdName='observable_id' onOptionChange={this.props.onOptionChange} selectedId={this.props.phenotype.observable_id} setNewValue={false} />

        <div onClick={()=>window.open('https://www.yeastgenome.org/ontology/phenotype/ypo', 'ypo')}><font color='blue'><strong>Yeast Phenotype Ontology</strong></font><p></p></div>
          
        {/* Qualifer */}
        <PulldownSection sec_title=' Qualifier' name='qualifier_id' value={this.props.phenotype.qualifier_id} onOptionChange={this.props.onOptionChange} />

        {/* Strain_background */}
        <PulldownSection sec_title='Strain_background' name='taxonomy_id' value={this.props.phenotype.taxonomy_id} onOptionChange={this.props.onOptionChange} />

        {/* Strain_name */}
        <CommentSection sec_title='Strain_name' name='strain_name' value={this.props.phenotype.strain_name} onOptionChange={this.props.onOptionChange} placeholder='Enter strain_name' rows='3' cols='500' />

        {/* details */}          
        <CommentSection sec_title='Details' name='details' value={this.props.phenotype.details} onOptionChange={this.props.onOptionChange} placeholder='Enter details' rows='3' cols='500' />

        {/* Allele */}
        <AutocompleteSection sec_title='Allele' id='allele_id' value1='display_name' value2='' selectedIdName='allele_id' placeholder='Enter allele' onOptionChange={this.props.onOptionChange} selectedId={this.props.phenotype.allele_id} setNewValue={true} />

        <div onClick={()=>window.open('https://www.rapidtables.com/math/symbols/greek_alphabet.html', 'greek')}><font color='blue'><strong>Greek alphabet letters & symbols</strong></font><p></p></div>

        {/* Allele_comment */}      
        <CommentSection sec_title='Allele_comment' name='allele_comment' value={this.props.phenotype.allele_comment} onOptionChange={this.props.onOptionChange} placeholder='Enter allele comment' rows='3' cols='500' />

        {/* Reporter */}
        <AutocompleteSection sec_title='Reporter' id='reporter_id' value1='display_name' value2='' selectedIdName='reporter_id' placeholder='Enter reporter' onOptionChange={this.props.onOptionChange} selectedId={this.props.phenotype.reporter_id} setNewValue={true} />

        {/* Reporter_comment */}
        <CommentSection sec_title='Reporter_comment' name='reporter_comment' value={this.props.phenotype.reporter_comment} onOptionChange={this.props.onOptionChange} placeholder='Enter reporter comment' rows='3' cols='500' />
      </div>
    );
  }
}

OneAnnotation.propTypes = {
  phenotype: PropTypes.object,
  onOptionChange: PropTypes.func
};

export default OneAnnotation;
