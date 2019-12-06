import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';
import { setData } from '../../actions/litGuideActions';
import PulldownMenu from './pulldownMenu';

const UPDATE_LITGUIDE = '/literature_guide_update';
const ADD_LITGUIDE = '/literature_guide_add';

const TIMEOUT = 300000;

class EditLitGuide extends Component {
  constructor(props) {
    super(props);

    this.handleChange = this.handleChange.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleUnlinkTag = this.handleUnlinkTag.bind(this);
    this.handleUnlinkTopic = this.handleUnlinkTopic.bind(this);
    this.handleUnlinkBoth = this.handleUnlinkBoth.bind(this);
    this.onUpdate = this.onUpdate.bind(this);
    this.handleAdd = this.handleAdd.bind(this);
    this.handleNoGeneUnlink = this.handleNoGeneUnlink.bind(this);
    this.onAdd = this.onAdd.bind(this);
    this.state = {
      pmid: null,
      gene_list: '',
      citation: '',
      gene_count: 0,
    };
  }

  componentDidMount() {
    this.setVariables();
  }

  handleChange() {
    let currentData = {};
    let data = new FormData(this.refs.form);
    for (let key of data.entries()) {
      currentData[key[0]] = key[1];
    }
    this.props.dispatch(setData(currentData));
  }

  handleUpdate(e) {
    e.preventDefault();
    this.onUpdate(e, '');
  }
    
  handleUnlinkTag(e) {
    e.preventDefault();
    this.onUpdate(e, 'tag');
  }

  handleUnlinkTagOnly(e) {
    e.preventDefault();
    this.onUpdate(e, 'tagOnly');
  }

  handleUnlinkTopic(e) {
    e.preventDefault();
    this.onUpdate(e, 'topic');
  }

  handleUnlinkBoth(e) {
    e.preventDefault();
    this.onUpdate(e, 'both');
  }

  handleAdd(e) {
    e.preventDefault();
    this.onAdd(e, '');
  }
  
  handleNoGeneUnlink(e) {
    e.preventDefault();
    this.onAdd(e, 'tag');
  }

  onUpdate(e, type) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.litguide){
      formData.append(key,this.props.litguide[key]);
    }
    let gene_id_list = this.getGeneIdList();
    formData.append('gene_id_list', gene_id_list);
    formData.append('unlink', type);
    fetchData(UPDATE_LITGUIDE, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      timeout: TIMEOUT
    }).then((data) => {
      this.props.dispatch(setMessage(data.success));
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  onAdd(e, type) {
    e.preventDefault();
    let formData = new FormData();
    for(let key in this.props.litguide){
      formData.append(key,this.props.litguide[key]);
    }
    formData.append('unlink', type);
    fetchData(ADD_LITGUIDE, {
      type: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      timeout: TIMEOUT
    }).then((data) => {
      this.props.dispatch(setMessage(data.success));
    }).catch((err) => {
      this.props.dispatch(setError(err.error));
    });
  }

  addButtons() {

    if (this.state.gene_list == '') {
      return (
        <div>
          <div className='row'>
            <div className='columns medium-6 small-6'>
              <button type='submit' id='submit' className="button expanded" onClick={this.handleAdd.bind(this)} > Add/Update tag/topic </button>
            </div>
            <div className='columns medium-6 small-6'>
              <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to unlink tthe curation tag from this paper? This action may not be possible to reverse.')) this.handleNoGeneUnlink(e); }} > Unlink tag from this paper </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div>
        <div className='row'>
          <div className='columns medium-3 small-3'>
            <button type='submit' id='submit' className="button expanded" onClick={this.handleUpdate.bind(this)} > Update tag/topic for selected genes </button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to unlink the curation tag frem the slected gene(s)? This action may not be possible to reverse.')) this.handleUnlinkTag(e); }} > Unlink tag from selected gene(s) </button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to unlink the literature topic from the selected gene(s)? This action may not be possible to reverse.')) this.handleUnlinkTopic(e); }} > Unlink topic from selected gene(s) </button>
          </div>
          <div className='columns medium-3 small-3'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to unlink the curation_tag/literature topic from the selected gene(s)? This action may not be possible to reverse.')) this.handleUnlinkBoth(e); }} > Unlink tag/topic from selected gene(s) </button>
          </div>
        </div>
      </div>
    );
  }

  getGeneIdList() {
    let gl = document.getElementById('gene_list');
    let gene_id_list = '';
    for (let i = 0; i < gl.options.length; i++) {
      if (gl.options[i].selected) { 
        if (gene_id_list != '') {
          gene_id_list = gene_id_list + ' ';
        }
        gene_id_list = gene_id_list + gl.options[i].value;
      }
    }
    return gene_id_list;
  }

  setVariables() {
    let urlList = window.location.href.split('/');
    let id = urlList[urlList.length-1];
    let genesID = 'genes_' + id;
    let tagID = 'tag_id_' + id;
    let gene_list = window.localStorage.getItem(genesID);
    let data = window.localStorage.getItem(tagID);
    let pieces = data.split('|');
    let pmid = pieces[0];
    let tag = pieces[1];
    let topic = pieces[2];
    let citation = pieces[3];
    let genes = gene_list.split(' ');
    let gene_count = genes.length;
    let values = genes.map((identifier, index) => {
      let names = identifier.split('|');
      if (gene_count == 1) {
        return <option value={identifier} key={index} selected> {names[0]} </option>;
      }
      else {
        return <option value={identifier} key={index}> {names[0]} </option>;
      }
    });
    this.setState({ id_to_gene: values,
      old_tag: tag,
      gene_list: gene_list, 
      pmid: pmid,
      citation: citation,
      gene_count: gene_count 
    });
    let currentData = {'tag': tag, 'topic': topic, 'pmid': pmid, 'old_tag': tag};
    this.props.dispatch(setData(currentData));
  }

  geneList() {

    if (this.state.gene_list == '') {
      return (
        <div className='row'>
          <div className='columns medium-12'>
            <div> Enter one or more genes ('|' delimited) (optional): </div>
            <input type='text' name='genes' value={this.props.litguide.genes} onChange={this.handleChange} />
          </div>
        </div>
      );  
    }

    return (
      <div className='row'>
        <div className='columns medium-12'>
          <div className='row'>
            <div className='columns medium-12'>
              <label> Choose one or more Genes: (select or unselect multiple genes by pressing the Control (PC) or Command (Mac) key while clicking)
              </label>
            </div>
          </div>
          <div className='row'>
            <div className='columns medium-12'>
              <select ref='gene_list' id='gene_list' value={this.props.litguide.gene_list} onChange={this.handleChange} size={this.state.gene_count} multiple>
                {this.state.id_to_gene}
              </select>
            </div>
          </div>
      </div>
      </div>
    );
  }

  linkButtons() {
    let sgdURL = 'https://www.yeastgenome.org/reference/' + this.state.pmid; 
    let pubmedURL = 'https://www.ncbi.nlm.nih.gov/pubmed/' + this.state.pmid;
    return (
      <div className='row'>
         <div className='columns medium-4'>
           <div className='columns small-6'>
             <button type='button' className='button expanded' onClick={()=>window.open(sgdURL, '_blank', 'location=yes,height=600,width=800,scrollbars=yes,status=yes')}> SGD Paper </button>
           </div>
           <div className='columns small-6'>
             <button type='button' className='button expanded' onClick={()=>window.open(pubmedURL, '_blank', 'location=yes,height=600,width=800,scrollbars=yes,status=yes')}> PubMed </button>
           </div>
         </div>
      </div>
    );
  }

  displayForm() {
    return (
      <div>
        <strong>{this.state.citation} (PMID:{this.state.pmid})</strong><p></p>
        {this.linkButtons()}
        <hr></hr>
        <form onSubmit={this.handleUpdate} ref='form'>
          {this.geneList()}
          <input type='hidden' name='pmid' value={this.state.pmid} />
          <input type='hidden' name='old_tag' value={this.state.old_tag} />
          <div className='row'>
            <div className='columns medium-12'>
              <div className='row'>
                <div className='columns medium-12'>
                  <div className='columns small-6'>
                    <div> Curation tag: </div>
                    <PulldownMenu name='tag' value={this.props.litguide.tag} onOptionChange={this.handleChange} />
                  </div>
                  <div className='columns small-6'>
                    <div> Literature topic: </div>
                    <PulldownMenu name='topic' value={this.props.litguide.topic} onOptionChange={this.handleChange} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {this.addButtons()}
        </form>

      </div>
    );
  }

  render() {
    if (this.state.citation) {
      return this.displayForm();
    }
    else {
      return (<div>Something is wrong while we are constructing the update form.</div>);
    }
  }
}

EditLitGuide.propTypes = {
  dispatch: PropTypes.func,
  litguide: PropTypes.object
};


function mapStateToProps(state) {
  return {
    litguide: state.litguide['curationData']
  };
}

export default connect(mapStateToProps)(EditLitGuide);
