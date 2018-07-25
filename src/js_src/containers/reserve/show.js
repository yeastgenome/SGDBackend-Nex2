import React, { Component } from 'react';
import { connect } from 'react-redux';
import { push } from 'react-router-redux';
import { Link } from 'react-router';

import CategoryLabel from '../../components/categoryLabel';
import CurateLayout from '../curateHome/layout';
import DeleteButton from '../../components/deleteButton';
import DetailList from '../../components/detailList';
import { setError, setMessage } from '../../actions/metaActions';
import fetchData from '../../lib/fetchData';
import Loader from '../../components/loader';

const DATA_BASE_URL = '/reservations';
const DISPLAY_KEYS = ['reservation_status', 'display_name', 'name_description', 'systematic_name', 'reservation_date', 'expiration_date', 'submitter_name', 'submitter_email', 'reference', 'notes'];

class GeneNameReservation extends Component {
  constructor(props) {
    super(props);
    this.state = {
      data: null
    };
  }

  componentDidMount() {
    let url = `${DATA_BASE_URL}/${this.props.params.id}`;
    fetchData(url).then( _data => {
      this.setState({ data: _data });
    });
  }

  handleDelete() {
    this.props.dispatch(push({ pathname: 'reservations' }));
    this.props.dispatch(setMessage('Gene name reservation was deleted.'));
  }

  handleExtend(e) {
    e.preventDefault();
    if (window.confirm('Are you sure you want to extend the gene name reservation?')) {
      let url = `${DATA_BASE_URL}/${this.props.params.id}/extend`;
      let reqOptions = {
        type: 'PUT',
        headers: {
          'X-CSRF-Token': window.CSRF_TOKEN
        }
      };
      this.setState({ isPending: true });
      let oldData = this.state.data;
      fetchData(url, reqOptions).then( _data => {
        this.setState({ data: _data, isPending: false });
        this.props.dispatch(setMessage('Gene name reservation successfully extended.'));
      }).catch( (data) => {
        let errorMessage = data ? data.message : 'Unable to extend gene name reservation.';
        this.props.dispatch(setError(errorMessage));
        this.setState({ isPending: false, data: oldData });
      });
    }
  }

  handlePromote(e) {
    e.preventDefault();
    if (window.confirm('Are you sure you want to promote the gene name reservation?')) {
      let oldData = this.state.data;
      this.setState({ data: null });
      let url = `${DATA_BASE_URL}/${this.props.params.id}/promote`;
      let successMessage = 'The new gene name reservation was added. It may take a day to show up in the search.';
      let reqOptions = {
        type: 'PUT',
        headers: {
          'X-CSRF-Token': window.CSRF_TOKEN
        }
      };
      this.setState({ isPending: true });
      fetchData(url, reqOptions).then( _data => {
        this.setState({ data: _data });
        this.props.dispatch(push({ pathname: 'reservations' }));
        this.props.dispatch(setMessage(successMessage));
      }).catch( (data) => {
        let errorMessage = data ? data.message : 'Unable to promote gene name.';
        this.props.dispatch(setError(errorMessage));
        this.setState({ isPending: false, data: oldData });
      });
    }
  }

  renderRes() {
    let data = this.state.data;
    let editUrl = `${DATA_BASE_URL}/${this.props.params.id}/edit`;
    if (data) {
      return (
        <div>
          <h3><CategoryLabel category='reserved_name' hideLabel /> Reserved Gene Name: {data.display_name}</h3>
          <Link to={editUrl}><i className='fa fa-edit' /> Edit</Link>
          <DetailList data={data} fields={DISPLAY_KEYS} />
        </div>
      );
    }
    return <Loader />;
  }

  renderExtendNode() {
    let data = this.state.data;
    let reservation_status = data ? data.reservation_status : false;
    if (reservation_status === 'Reserved') {
      return <a className='button secondary' onClick={this.handleExtend.bind(this)}>Extend gene name reservation by 1 year</a>;
    }
    return null;
  }

  renderActions() {
    let data = this.state.data;
    let deleteUrl = `${DATA_BASE_URL}/${this.props.params.id}`;
    let reservation_status = data ? data.reservation_status : false;
    let promoteNode;
    if (reservation_status === 'Unprocessed') {
      promoteNode = <a className='button primary' onClick={this.handlePromote.bind(this)}><i className='fa fa-check' /> Add Gene Name Reservation</a>;
    } else {
      let stLink = `${DATA_BASE_URL}/${this.props.params.id}/standardize`;
      promoteNode = <Link className='button primary' to={stLink}><i className='fa fa-check' /> Standardize Gene Name</Link>;
    }
    return (
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '3rem' }}>
        {promoteNode}
        {this.renderExtendNode()}
        <DeleteButton label='Discard gene name reservation' url={deleteUrl} onSuccess={this.handleDelete.bind(this)} />
      </div>
    );
  }

  render() {
    return (
      <CurateLayout>
        <div>
          {this.renderRes()}
          {this.renderActions()}
        </div>
      </CurateLayout>
    );
  }
}

GeneNameReservation.propTypes = {
  params: React.PropTypes.object,
  dispatch: React.PropTypes.func
};

function mapStateToProps() {
  return {
  };
}

export default connect(mapStateToProps)(GeneNameReservation);
