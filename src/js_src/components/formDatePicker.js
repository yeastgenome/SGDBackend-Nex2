import React, {Component} from 'react';
import DatePicker from 'react-datepicker';
import moment from 'moment';

import 'react-datepicker/dist/react-datepicker.css';
/* eslint-disable no-debugger */
class FormDatePicker extends Component{
  constructor(props){
    super(props);
    this.state = {
      startDate: moment().toDate()
    };

    this.handleChange = this.handleChange.bind(this);

  }
  handleChange(date) {
    this.setState({startDate: date});
  }

  render(){
    let dt = <DatePicker onChange={this.handleChange} />;
    //debugger;
    return <div>{dt}<div></div><div>Not Found</div></div>;
  }
}

export default FormDatePicker;
