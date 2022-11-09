import React, { Component } from 'react';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import { push } from 'connected-react-router';
import t from 'tcomb-form';
import PropTypes from 'prop-types';
import style from './style.css';
import FlexiForm from '../../components/forms/flexiForm';
import { authenticateUser } from '../../actions/authActions';
import { parse } from 'query-string';
import {updateColleagueCount,updateGeneCount, updateAuthorResponseCount, setError} from '../../actions/metaActions';
const DEFAULT_AUTH_LANDING = '/';

class Login extends Component {
  renderDBLogin() {
    let loginSchema = t.struct({
      username: t.String,
      password: t.String
    });
    let loginOptions = {
      fields: {
        password: {
          type: 'password'
        }
      }
    };
    let _onSuccess = (data) => {
      getCounts();
      let nextUrl = parse(this.props.queryParams).next || DEFAULT_AUTH_LANDING;
      this.props.dispatch(authenticateUser(data));
      this.props.dispatch(push(nextUrl));
    };
    let _onError = (data) => {
      this.props.dispatch(setError(data.error));
    };
    
    let getCounts = () => {
      fetch('/triage_count')
      .then(count => count.json())
      .then(count => {
        if(count.hasOwnProperty('message')){
          this.props.dispatch(setError(count.message));
        }
        else{
          this.props.dispatch(updateColleagueCount(count.colleagueCount));
          this.props.dispatch(updateGeneCount(count.geneCount));
          this.props.dispatch(updateAuthorResponseCount(count.authorResponseCount));
        }
      });
    };

    return (
      <div className='columns small-6'>
        <h5>Option 1</h5>
        <p>Enter your database username and password.</p>
        <div style={{ margin: '0 auto', maxWidth: '20rem', textAlign: 'left' }}>
          <FlexiForm requestMethod='POST' tFormOptions={loginOptions} tFormSchema={loginSchema} onSuccess={_onSuccess} onError={_onError} submitText='Login' updateUrl='/db_sign_in' />
        </div>
      </div>
    );
  }

  renderGLogin() {
    return (
      <div className='columns small-6'>
        <h5>Option 2</h5>
        <p>Sign into Google using your Stanford email address, or logout of other Google accounts.</p>
        <Link className={`${style.beginLoginButton} button`} to='/google_login'>Verify SUNet ID with Google</Link>
      </div>
    );
  }

  render() {
    return (
      <div className={`callout ${style.loginContainer}`}>
        <div className='row'>
          {this.renderDBLogin()}
          {this.renderGLogin()}
        </div>
      </div>
    );
  }
}

Login.propTypes = {
  dispatch: PropTypes.func,
  queryParams: PropTypes.string
};

function mapStateToProps(_state) {
  return {
    queryParams: _state.router.location.search
  };
}

export default connect(mapStateToProps)(Login);
