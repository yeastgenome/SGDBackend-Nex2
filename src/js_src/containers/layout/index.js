import React, { Component, PropTypes } from 'react';
import { Link } from 'react-router';
import { connect } from 'react-redux';

// import * as AuthActions from '../actions/auth_actions';
import style from './style.css';
// import SearchBar from './searchBar';

class Layout extends Component {
  render() {
    console.log('layout');
    let onClickLogout = e => {
      e.preventDefault();
      // this.props.dispatch(AuthActions.logoutAndRedirect());
    };
    // init auth nodes, either login or logout links
    let authNodes = this.props.isAuthenticated ?
      <ul className={`menu ${style.authMenu}`}><li><a className={style.navLink} onClick={onClickLogout} href='#'><i className='fa fa-sign-out'></i> Logout</a></li></ul> :
      <ul className={`menu ${style.authMenu}`}><li><Link className={style.navLink} to='/login'><i className='fa fa-sign-in'></i> Login</Link></li></ul>;
    return (
      <div>
        <nav className={`top-bar ${style.navWrapper}`}>
          <div className='top-bar-left'>
            <ul className={`menu ${style.menu}`}>
              <li>
                <Link to='curate' className={style.indexLink}>
                  <img src='/static/img/sgd_logo.png' className={style.imgLogo} />
                  <span className={`${style.logoText} ${style.navLink}`}>Curator</span>
                </Link>
              </li>
            </ul>
          </div>
          <div className='top-bar-right'>
            {authNodes}
          </div>
        </nav>
        <div className='row full-width wrapper'>
          <div className='large-12 columns'>
            {this.props.children}
          </div>
        </div>
      </div>
    );
  }
}

Layout.propTypes = {
  children: PropTypes.node,
  dispatch: React.PropTypes.func,
  isAuthenticated: React.PropTypes.bool
};

function mapStateToProps(_state) {
  let state = _state.auth;
  return {
    isAuthenticated: state.isAuthenticated
  };
}

export default connect(mapStateToProps)(Layout);
