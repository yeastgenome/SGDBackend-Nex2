import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import { connect } from 'react-redux';
/* eslint-disable no-debugger */

//const BASE_CURATE_URL = 'curate/file';

class FileCurateUpdate extends Component{
  render(){
    return(
      <CurateLayout>
        <div className='row'>
          <p>File curate page</p>
        </div>
      </CurateLayout>
    );
  }

}

function mapStateToProps(state){
  return state;
}

export default connect(mapStateToProps)(FileCurateUpdate);
