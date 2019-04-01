import React, { Component } from 'react';
import CurateLayout from '../curateHome/layout';
import Loader from '../../components/loader';
import fetchData from '../../lib/fetchData';
import { setError, setMessage } from '../../actions/metaActions';
import { connect } from 'react-redux';
import style from './style.css' ;
import {setURL,setCode,setSubject,setRecipients} from '../../actions/newsLetterActions';

const RECIPIENT_URL = '/colleagues_subscriptions';
const SOURCE_URL = '/get_newsletter_sourcecode';
const SEND_EMAIL = '/send_newsletter';
const VISIBLE_ERROR = 'form-error is-visible';
const INVISIBLE_ERROR = 'form-error';

class NewsLetter extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isPending: false,

      urlError:INVISIBLE_ERROR,
      codeError:INVISIBLE_ERROR,
      subjectError:INVISIBLE_ERROR,
      recipientsError:INVISIBLE_ERROR,

      isSubmitButtonDisabled : true
    };

    this.handleCodeChange = this.handleCodeChange.bind(this);
    this.handleSubmitURL = this.handleSubmitURL.bind(this);
    this.handleUrlChange = this.handleUrlChange.bind(this);
    this.handleRenderCode = this.handleRenderCode.bind(this);

    this.handleSendEmail = this.handleSendEmail.bind(this);
    this.handleSubjectChange = this.handleSubjectChange.bind(this);
    this.handleRecipientsChange = this.handleRecipientsChange.bind(this);
    this.handleGettingRecipients = this.handleGettingRecipients.bind(this);

    this.handleErrorChecking = this.handleErrorChecking.bind(this);
  }
  

  handleUrlChange(event) {
    this.props.updateURL(event.target.value);
    this.props.updateCode('');

    if(event.target.value.length== 0){
      this.setState({urlError:VISIBLE_ERROR},this.handleErrorChecking);
    }
    else{
      this.setState({urlError:INVISIBLE_ERROR});
    }
  }

  handleSubmitURL() {
    this.setState({ isPending: true});
    this.setCode('');

    fetchData(SOURCE_URL, {
      type: 'POST',
      data: {
        url: this.props.url
      }
    }).then((data) => {
      this.setState({ isPending: false,codeError:INVISIBLE_ERROR },this.handleErrorChecking);
      this.setCode(data.code);
    }).catch((data) => {
      this.setState({ isPending: false },this.handleErrorChecking);
      this.props.dispatch(setError(data.error));
    });

  }

  handleRenderCode() {
    if (this.state.isPending) return <Loader />;
    return (<textarea name="code" rows="26" cols="10" onChange={this.handleCodeChange} value={this.props.code}></textarea>);
  }

  preview() {
    let htmlText = () => ({ __html: this.props.code });
    return (
      <div dangerouslySetInnerHTML={htmlText()}></div>
    );
  }

  handleCodeChange(event) {
    this.setCode(event.target.value);

    if(event.target.value.length== 0){
      this.setState({codeError:VISIBLE_ERROR},this.handleErrorChecking);
    }
    else{
      this.setState({codeError:INVISIBLE_ERROR},this.handleErrorChecking);
    }
  }

  handleSubjectChange(event) {
    this.setSubject(event.target.value);

    if(event.target.value.length == 0){
      this.setState({subjectError:VISIBLE_ERROR},this.handleErrorChecking);
    }
    else{
      this.setState({subjectError:INVISIBLE_ERROR},this.handleErrorChecking);
    }
  }

  handleRecipientsChange(event) {
    this.setSubject(event.target.value);

    if(event.target.value.length == 0){
      this.setState({recipientsError:VISIBLE_ERROR},this.handleErrorChecking);
    }
    else{
      this.setState({recipientsError:INVISIBLE_ERROR},this.handleErrorChecking);
    }
  }

  handleGettingRecipients() {
    this.setRecipients('');

    fetchData(RECIPIENT_URL, {
      type: 'GET'
    }).then((data) => {
      this.setRecipients(data.colleagues);
      this.setState({recipientsError:INVISIBLE_ERROR },this.handleErrorChecking);
    }).catch((data) => {
      this.props.dispatch(setError(data.error),this.handleErrorChecking);
    });
  }

  handleSendEmail() {

    if (window.confirm('Are you sure, sending this newsletter?')) {
      fetchData(SEND_EMAIL, {
        type: 'POST',
        data: {
          html: this.props.code, subject: this.props.subject, recipients: this.props.recipients
        }
      }).then((data) => {
        this.props.dispatch(setMessage(data.success));
      }).catch((data) => {
        this.props.dispatch(setError(data.error));
      });
    }
  }

  handleErrorChecking(){
    if(this.props.url.length > 0 && this.props.code.length > 0 && this.props.subject.length > 0 && this.state.props.length > 0 ){
      this.setState({isSubmitButtonDisabled: false});
    }
    else{
      this.setState({isSubmitButtonDisabled: true});
    }
  }

  render() {
    return (
      <CurateLayout>
        {
          <form>

            <div className="row">
              <div className="columns large-12">
                <h1>NewsLetter</h1>

                {/* URL Label*/}
                <div className="row">
                  <div className="columns medium-12">
                    <label> URL </label>
                  </div>
                </div>
                
                {/* URL*/}
                <div className="row">
                  <div className="columns medium-8">
                    <input type="url" name="url" placeholder="Enter URL for newsletter" value={this.props.url} onChange={this.handleUrlChange} />
                    <label data-alert className={this.state.urlError}>URL is required</label>
                  </div>
                  <div className="columns medium-4">
                    <button type="button" onClick={this.handleSubmitURL} className="button">Get source code</button>
                  </div>
                </div>

                {/* Source code */}
                <div className="row">
                  <div className="column medium-6 large-6">
                    <div className="row">
                      <div className="column medium-12 large-12">
                        <label>HTML Code</label>
                      </div>
                    </div>
                    <div className="row">
                      <div className="column medium-12 large-12">
                        {this.handleRenderCode()}
                        <label data-alert className={this.state.codeError}>HTML code is required</label>
                      </div>
                    </div>
                  </div>

                  <div className="column medium-6 large-6">
                    <div className="row">
                      <div className="column medium-12 large-12">
                        <label>Preview Area</label>
                      </div>
                    </div>
                    <div className="row">
                      <div className={`column medium-12 large-11 ${style.previewBox}`}>
                        {this.preview()}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Subject line */}
                <div className="row">
                  <label className="columns medium-12 large-9">Subject Line
                  <input type="url" placeholder="Enter newsletter subject line" value={this.props.subject} name="subject" onChange={this.handleSubjectChange} />
                  <label data-alert className={this.state.subjectError}>Subject line is required</label>
                  </label>
                </div>

                {/* Recipients Label */}
                <div className="row">
                  <div className="large-8 columns">
                    <label>Recipients</label>
                  </div>
                </div>

                {/* Recipients*/}
                <div className="row">
                  <div className="large-8 columns">
                    <textarea name="recipients" rows="3" cols="10" type="url" placeholder="Enter emails with ; seperated" value={this.props.recipients} onChange={this.handleRecipientsChange} />
                    <label data-alert className={this.state.recipientsError}>Recipient(s) is required</label>
                  </div>

                  <div className="large-4 columns">
                    <button type="button" onClick={this.handleGettingRecipients} className="button">Get recipients from database</button>
                  </div>

                </div>

                {/* Send button */}
                <div className="row">
                  <div className="columns large-12">
                    <button type="button" onClick={this.handleSendEmail} className="button" disabled={this.state.isSubmitButtonDisabled}>Send Email</button>
                  </div>
                </div>
              </div>
            </div>

          </form>
        }
      </CurateLayout>);
  }
}

NewsLetter.propTypes = {
  url:React.PropTypes.string,
  code:React.PropTypes.string,
  subject:React.PropTypes.string,
  recipients:React.PropTypes.string,
  dispatch: React.PropTypes.func,
  updateURL:React.PropTypes.func,
  updateCode:React.PropTypes.func,
  updateRecipients:React.PropTypes.func,
  updateSubject:React.PropTypes.func,
};

function mapStateToProps(state) {
  return {
    url:state.url,
    code:state.code,
    subject:state.subject,
    recipients:state.recipients
  };
}

function mapDispatchToProps(dispatch){
  return {
    updateURL : (url) => {dispatch(setURL(url));},
    updateCode: (code) => {dispatch(setCode(code));},
    updateSubject:(subject) => {dispatch(setSubject(subject));},
    updateRecipients: (recipients) =>{dispatch(setRecipients(recipients));}
  };
}

// export default NewsLetter;
export default connect(mapStateToProps,mapDispatchToProps)(NewsLetter);
