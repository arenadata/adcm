// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { StartPage } from './start.po';
import { LoginPage } from '../login/login.po';
import { browser } from 'protractor';

describe('Start page', () => {
  let page: StartPage;
  let login: LoginPage;

  beforeEach(() => {
    page = new StartPage();
    login = new LoginPage();
  });

  it('when user is authorize', () => {
    login.navigateTo();
    login.fillCredentials();
    browser.sleep(1);
    page.navigateTo();    
    expect(page.getPageTitleText()).toEqual('Hi there!');
  });
});
