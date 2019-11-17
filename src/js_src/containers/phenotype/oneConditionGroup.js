import React, { Component } from 'react';
import PropTypes from 'prop-types';
import ConditionSection from './conditionSection';

class OneConditionGroup extends Component {
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
        {/* Chemicals */}
        <ConditionSection sec_title='Chemical(s) (Enter CHEBI ID (eg, CHEBI:5856)) ("|" delimited)' class='chemical' name={this.props.phenotype.chemical_name} value={this.props.phenotype.chemical_value} unit={this.props.phenotype.chemical_unit} onOptionChange={this.props.onOptionChange} />

        <div onClick={()=>window.open('https://www.ebi.ac.uk/chebi/', 'chebi')}><font color='blue'><strong>Search Chebi Ontology</strong></font><p></p></div>

        {/* Media */}
        <ConditionSection sec_title='Media ("|" delimited)' class='media' name={this.props.phenotype.media_name} value={this.props.phenotype.media_value} unit={this.props.phenotype.media_unit} onOptionChange={this.props.onOptionChange} />

        {/* temperature */}
        <ConditionSection sec_title='Temperature(s) ("|" delimited)' class='temperature' name={this.props.phenotype.temperature_name} value={this.props.phenotype.temperature_value} unit={this.props.phenotype.temperature_unit} onOptionChange={this.props.onOptionChange} isTemperature={true} />

        {/* treatment */}
        <ConditionSection sec_title='Treatment(s) ("|" delimited)' class='treatment' name={this.props.phenotype.treatment_name} value={this.props.phenotype.treatment_value} unit={this.props.phenotype.treatment_unit} onOptionChange={this.props.onOptionChange}  />

        {/* assay */}
        <ConditionSection sec_title='Assay' class='assay' name={this.props.phenotype.assay_name} value={this.props.phenotype.assay_value} unit={this.props.phenotype.assay_unit} onOptionChange={this.props.onOptionChange} isAssay={true} />

        {/* phase */}
        <ConditionSection sec_title='Phase(s) ("|" delimited)' class='phase' name={this.props.phenotype.phase_name} value={this.props.phenotype.phase_value} unit={this.props.phenotype.phase_unit} onOptionChange={this.props.onOptionChange}  />

        {/* radiation */}
        <ConditionSection sec_title='Radiation(s) ("|" delimited)' class='radiation' name={this.props.phenotype.radiation_name} value={this.props.phenotype.radiation_value} unit={this.props.phenotype.radiation_unit} onOptionChange={this.props.onOptionChange}  />
      
      </div>
    );
  }
}

OneConditionGroup.propTypes = {
  phenotype: PropTypes.object,
  onOptionChange: PropTypes.func
};

export default OneConditionGroup;
