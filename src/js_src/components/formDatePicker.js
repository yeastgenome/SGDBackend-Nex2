import React, {Component} from 'react';
import moment from 'moment';
import DatePicker from 'react-datepicker';
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
    return (
        <div>
          <DatePicker selected={moment(this.state.startDate)} onChange={this.handleChange} />
        </div>
    );
  }
}

export default FormDatePicker;
