import React, { Component } from 'react';
import PropTypes from 'prop-types';
import fetchData from '../../lib/fetchData';
import { connect } from 'react-redux';
import { setError, setMessage } from '../../actions/metaActions';

const UPDATE_TRACK = '/datasettrack_update';
const DELETE_TRACK = '/datasettrack_delete';

const TIMEOUT = 300000;

class OneTrack extends Component {
  constructor(props) {
    super(props);

    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleDelete = this.handleDelete.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.state = {
      data: {},
      format_name: null,
    };
  }

  componentDidMount() {
    this.setData();
  }	
    
  handleUpdate(e) {
    e.preventDefault();
    this.updateData(UPDATE_TRACK);
  }

  handleDelete(e) {
    e.preventDefault();
    this.updateData(DELETE_TRACK);
  }

  updateData(update_url) {
    let formData = new FormData();
    for(let key in this.state.data){
      formData.append(key,this.state.data[key]);
    }  
    fetchData(update_url, {
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
    
  handleChange() {
    let currentTrack = {};
    let data = new FormData(this.refs.form); 
    for (let key of data.entries()) {
      currentTrack[key[0]] = key[1];
    }
    this.setState({ data: currentTrack });  
  }

  setData() {
    this.setState({ data: this.props.data });
  }
    
  trackRow() {
    return (
      <div>
        {/* format_name, display_name */}
        <div className='row'>
          <div className='columns medium-4 small-4'>
            <div> <label> format_name </label> </div>
            <input type='text' name='format_name' value={this.state.data.format_name} onChange={this.handleChange.bind(this)} />
          </div>
          <div className='columns medium-8 small-8'>
            <div> <label> display_name </label> </div>
            <input type='text' name='display_name' value={this.state.data.display_name} onChange={this.handleChange.bind(this)} />
          </div>
        </div>

        {/* obj_url & track_order */}
        <div className='row'>
          <div className='columns medium-10 small-10'>
            <div> <label> obj_url </label> </div>
            <input type='text' name='obj_url' value={this.state.data.obj_url} onChange={this.handleChange.bind(this)} />
          </div>
          <div className='columns medium-2 small-2'>
            <div> <label> track_order </label> </div>
            <input type='text' name='track_order' value={this.state.data.track_order} onChange={this.handleChange.bind(this)} />
          </div>
        </div>

        {/* update & delete button */}
        <div className='row'>	    
          <div className='columns medium-6 small-6'>
            <button type='submit' id='submit' value='0' className="button expanded" onClick={this.handleUpdate.bind(this)} > Update this track </button>
          </div>
          <div className='columns medium-6 small-6'>
            <button type='button' className="button alert expanded" onClick={(e) => { if (confirm('Are you sure you want to delete this track?')) this.handleDelete(e); }} > Delete this track </button>
          </div>
        </div>
      </div>
    );
  }
    
  render() {
    //let formName = 'form' + this.props.index;
    return (
      <div>
        <form onSubmit={this.handleUpdate} ref='form'>
          <input name='datasettrack_id' value={this.state.data.datasettrack_id} className="hide" />
          {this.trackRow()}
          <hr />
        </form>
      </div>
    );
  }
}

OneTrack.propTypes = {
  dispatch: PropTypes.func,
  data: PropTypes.object,
};

function mapStateToProps(state) {
  return {
    dataset: state.dataset['currentDataset']
  };
}

export default connect(mapStateToProps)(OneTrack);



