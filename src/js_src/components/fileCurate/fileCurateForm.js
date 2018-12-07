import React from 'react';
import TextField from '../forms/textField';
import StringField from '../forms/stringField';
import FormDatePicker from '../../components/formDatePicker';

const FileCurateForm = () => {
  return(
    <div>
      <div className={'row'} >
        <div className={'columns small-6'}>
          <StringField className={'columns small-6'} displayName={'Display Name'} />
        </div>
        <div className={'columns small-6'}>
          <StringField className={'columns small-6'} displayName={'Status'} />      </div>
        </div>

      <div className={'row'}>
        <div className={'columns small-6'}>
          <StringField className={'columns small-6 medium-6'} displayName={'keywords'} />
        </div>
        <div className={'columns small-6'}>
          <StringField className={'columns small-6 medium-6'} displayName={'Previous Filename'} />
        </div>
      </div>
      <div className={'row'}>
        <div className={'columns small-6'}><TextField  displayName={'Description'} /></div>
        <div className={'columns small-6 small-offset-5'}></div>
      </div>
      <div className={'row'}>
        <div className={'columns small-6'}><FormDatePicker /></div>
        <div className={'columns small-6 small-offset-5'}></div>
      </div>

    </div>
  );
};

export default FileCurateForm;
