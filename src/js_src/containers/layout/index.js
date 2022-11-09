import React, { Component} from 'react';
import { Link } from 'react-router-dom';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';
// import * as AuthActions from '../actions/auth_actions';
import style from './style.css';
import SearchBar from './searchBar';
import curateLogo from './curateLogo.png';
import Loader from './loader/index';
import { clearError, clearMessage } from '../../actions/metaActions';
import {updateColleagueCount, updateGeneCount, updateAuthorResponseCount} from '../../actions/metaActions';
import getPusherClient from '../../lib/getPusherClient';
const CHANNEL = 'sgd';
const GENECOUNTEVENT = 'geneCount';
const COLLEAGUECOUNTEVENT = 'colleagueCount';
const AUTHORRESPONSECOUNTEVENT = 'authorResponseCount';

class LayoutComponent extends Component {
  componentDidMount(){
    // this.listenForUpdates();
  }
  
  componentWillUnmount() {
    if (this.channel !== undefined) {
      this.channel.unbind(GENECOUNTEVENT);
      this.channel.unbind(COLLEAGUECOUNTEVENT);
      this.channel.unbind(AUTHORRESPONSECOUNTEVENT); 
    }
  }

  listenForUpdates() {
    if (this.channel == undefined) {
      let pusher = getPusherClient();
      this.channel = pusher.subscribe(CHANNEL);
      this.channel.bind(GENECOUNTEVENT, (data) => {
        this.props.dispatch(updateGeneCount(data.message));
      });
      this.channel.bind(COLLEAGUECOUNTEVENT, (data) => {
        this.props.dispatch(updateColleagueCount(data.message));
      });
      this.channel.bind(AUTHORRESPONSECOUNTEVENT, (data) => {
        this.props.dispatch(updateAuthorResponseCount(data.message));
      }); 
    }
  }

  renderSearch () {
    if (this.props.isAuthenticated) {
      return (
        <div>
          <ul className={`menu ${style.authMenu}`}>
            <li><SearchBar /></li>
          </ul>
        </div>
      );
    }
    return null;
  }

  renderPublicMenu() {
    return (
      <ul className={`menu ${style.topMenu}`}>
        <li>
          <Link className={style.indexLink} to='/'>
            <img className={style.imgLogo} src={curateLogo} />
          </Link>
        </li>
        <li>
          <Link to='help'>
            <span><i className='fa fa-question-circle' /> Help</span>
          </Link>
        </li>
      </ul>
    );
  }

  renderAuthedMenu() {
    return (
      <ul className={`menu ${style.topMenu}`}>
        <li>
          <Link className={style.indexLink} to='/'>
            <img className={style.imgLogo} src={curateLogo} />
          </Link>
        </li>
        <li>
          <Link to='/'>
            <span><i className='fa fa-home' /> Curation Home</span>
          </Link>
        </li>
        <li>
          <Link to='help'>
            <span><i className='fa fa-question-circle' /> Help</span>
          </Link>
        </li>
        <li>
          <a className={style.navLink} href='/signout'><i className='fa fa-sign-out' /> Logout</a>
        </li>
      </ul>
    );
  }
  
  renderError() {
    if (!this.props.error) return null;
    let handleClick = () => {
      this.props.dispatch(clearError());
    };
    return (
      <div className={`alert callout ${style.errorContainer}`}>
        <h3 className={style.closeIcon} onClick={handleClick}><i className='fa fa-close' /></h3>
        <p>
          {this.props.error}
        </p>
      </div>
    );
  }

  renderMessage() {
    if (!this.props.message) return null;
    let handleClick = () => {
      this.props.dispatch(clearMessage());
    };
    return (
      <div className={`primary callout ${style.errorContainer}`}>
        <h3 className={style.closeIcon} onClick={handleClick}><i className='fa fa-close' /></h3>
        <p dangerouslySetInnerHTML={{ __html: this.props.message}} />
      </div>
    );
  }

  renderBody() {
    return this.props.children;
  }

  render() {
    // init auth nodes, either login or logout links
    let menuNode = this.props.isAuthenticated ? this.renderAuthedMenu() : this.renderPublicMenu();
    this.props.isAuthenticated ? this.listenForUpdates() : '';
    let devNoticeNode = null;
    if (process.env.DEMO_ENV === 'development') {
      devNoticeNode = <div className={`warning callout ${style.demoWarning}`}><i className='fa fa-exclamation-circle' /> Demo</div>;
    }
    return (
      <div>
        {this.renderMessage()}
        {this.renderError()}
        {devNoticeNode}
        <nav className={`top-bar ${style.navWrapper}`}>
          <div className='top-bar-left'>
            {menuNode}
          </div>
          <div className='top-bar-right'>
            {this.renderSearch()}
          </div>
        </nav>
        <div className={`row ${style.contentRow}`}>
          <Loader />
          <div className={`large-12 columns ${style.contentContainer}`}>
            {this.renderBody()}
          </div>
        </div>
      </div>
    );
  }
}

LayoutComponent.propTypes = {
  children: PropTypes.node,
  error: PropTypes.string,
  message: PropTypes.string,
  dispatch: PropTypes.func,
  isAuthenticated: PropTypes.bool,
};

function mapStateToProps(state) {
  return {
    error: state.meta.get('error'),
    message: state.meta.get('message'),
    isAuthenticated: state.auth.get('isAuthenticated'),
  };
}

export { LayoutComponent as LayoutComponent };
export default connect(mapStateToProps)(LayoutComponent);
