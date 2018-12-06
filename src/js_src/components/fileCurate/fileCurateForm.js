import React from 'react';
import TextField from '../forms/textField';
import StringField from '../forms/stringField';
import { SMALL_COL_CLASS, LARGE_COL_CLASS } from '../../constants';

const FileCurateForm = () => {
  return(
    <div>
      <StringField displayName={'Display Name'} />
      <StringField displayName={'Status'} />
      <StringField displayName={'keywords'} />
      <StringField displayName={'Previous Filename'} />
      <TextField displayName={'Description'} />

    </div>
  );
};

export default FileCurateForm;
