/*eslint-disable no-undef */
/*eslint-disable no-unused-vars */
import React from 'react';
import intl from 'intl';

import { configure, shallow, render, mount } from 'enzyme';
import Adapter from 'enzyme-adapter-react-15.4';

configure({adapter: new Adapter()});
global.intl = intl;
global.shallow = shallow;
global.render = render;
global.mount = mount;
