import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import NewsLetter from './index';


class newsLetterWrapper extends Component{
  constructor(props){
    super(props);
  }

  render(){
    return(
      <CurateLayout>
          <NewsLetter />
      </CurateLayout>
    );
  }
}

export default newsLetterWrapper ;