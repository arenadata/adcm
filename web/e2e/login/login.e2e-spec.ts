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
import { StartPage } from '../start/start.po';
import { LoginPage } from './login.po';

describe('Login page', () => {
  let page: LoginPage;
  let startPage: StartPage;

  const wrongCredentials = {
    username: 'fake',
    password: 'fake',
  };

  beforeEach(() => {
    page = new LoginPage();
    startPage = new StartPage();
  });

  it('when user trying to login with wrong credentials', async () => {
    page.navigateTo();
    await page.fillCredentials(wrongCredentials);
    expect(page.getErrorMessage()).toEqual('Incorrect password or user.');
  });

  it('when login is successful — he should redirect to default page', async () => {
    page.navigateTo();
    await page.fillCredentials();    
    expect(startPage.getPageTitleText()).toEqual('Hi there!');    
  });

});
