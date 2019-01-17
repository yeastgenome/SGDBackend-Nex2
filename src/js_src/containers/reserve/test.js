import assert from 'assert';
import React from 'react';
import { renderToString } from 'react-dom/server';
import {shallow} from 'enzyme';
import { Provider } from 'react-redux';

import Reserve from './new';
import configureMockStore from 'redux-mock-store';



describe('Reserve', () => {
  it('should be able to render to an HTML string', () => {
    const mockStore = configureMockStore([]);
    const store = mockStore({});
    let htmlString = renderToString(shallow(<Provider store={store}><Reserve /></Provider>).html());
    assert.equal(typeof htmlString, 'string');
  });
});
