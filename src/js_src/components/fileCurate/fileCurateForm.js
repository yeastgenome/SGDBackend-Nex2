import React, { Component } from 'react';
import TextField from '../forms/textField';
import StringField from '../forms/stringField';
import FormDatePicker from '../../components/formDatePicker';
import Dropzone from 'react-dropzone';
import style from '../style.css';
/* eslint-disable no-debugger */

class FileCurateForm extends Component{
  constructor(props){
    super(props);
    this.handleClear = this.handleClear.bind(this);
    this.renderFileDrop = this.renderFileDrop.bind(this);
    this.state = {
      files: []
    };
  }
  handleClear(){
    this.state({ files:[]});
  }
  handleDrop(_files){
    this.setState({files: _files});

  }
  handleSubmit(e){
    e.preventDefault();
    debugger;
    let data = new FormData(this.refs.upForm);
    if(this.state.files){
      data.append('file', this.state.files[0]);
    }
    this.props.onFileUploadSubmit(data);

  }
  renderFileDrop(){
    if(this.state.files.length){
      let filename = this.state.files[0].name;
      return(
        <div>
          <p>{filename}</p>
        </div>
      );
    }
    return  (<Dropzone name={'file'} onDrop={this.handleDrop.bind(this)} multiple={false}>
                <p className={style.uploadMsg}>Drop file here or click to select.</p>
                <h3 className={style.uploadIcon}><i className='fa fa-cloud-upload' /></h3>
              </Dropzone>);
  }

  render(){
    return(
        <form ref='upForm' onSubmit={this.handleSubmit.bind(this)} name='test'>
          <div>
            <h1>Upload File to S3</h1>
            <hr />
            <h5>Directions</h5>
            <ul>
              <li>Make sure your file has header matching the following example: link to google sheets</li>
              <li>Acceptable file formats: <span className={'label'}>csv</span></li>
            </ul>
          </div>
          <hr />
          <div className={'row'} >
            <div className={'columns small-6'}>
              <StringField id='dname' className={'columns small-6'} paramName={'displayName'} displayName={'Display Name'} placeholder={'El Hage_2014_PMID_24532716'} isRequired={true} />
            </div>
            <div className={'columns small-6'}>
              <StringField id='status' className={'columns small-6'} paramName={'status'} displayName={'status'} defaultValaue={'active'} placeholder={'Active or Archive'} isRequired={true} />      </div>
            </div>

          <div className={'row'}>
            <div className={'columns small-6'}>
              <StringField value='x' id='gvariation' className={'columns small-6 medium-6'} paramName={'genomeVariation'} displayName={'keywords'} placeholder={'genome variation'} isRequired={true} />
            </div>
            <div className={'columns small-6'}>
              <StringField id='pfilename' className={'columns small-6 medium-6'} paramName={'previousFileName'} displayName={'Previous Filename'} />
            </div>
          </div>
          <div className={'row'}>
            <div id='description' className={'columns small-6'}><TextField className={`${style.txtBox}`} paramName={'description'}  displayName={'Description'} placeholder={'Genome-wide measurement of whole transcriptome versus histone modified mutants'} isRequired={true}  /></div>
            <div className={'columns small-6 small-offset-5'}></div>
          </div>
          <div className={'row'}>
            <div className={`columns small-6 ${style.dateComponent}`}>
              <label htmlFor="dPicker"> File Date </label>
              <FormDatePicker id="dPicker" /></div>
            <div className={'columns small-6 small-offset-5'}>
            </div>
          </div>
          <div className={'row'}>
            <div className={'columns small-6 small-offset-5'}></div>
          </div>
          <div className={'row'}>
            <div className={'columns small-6'}>
              {this.renderFileDrop()}
            </div>
          </div>

          <hr />
          <div className={'row'}>
            <div className={'columns small-3'}>
              <input type='submit' className='button' value='Submit' />
            </div>
            <div className={'columns small-3 small-offset-4'}></div>
          </div>

        </form>
    );

  }
}

FileCurateForm.propTypes = {
  onFileUploadSubmit: React.PropTypes.func
};

export default FileCurateForm;
