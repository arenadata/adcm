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
import { browser, by, element } from 'protractor';

export class LoginPage {
  private credentials = {
    username: 'admin',
    password: 'admin',
  };

  navigateTo() {
    return browser.get('/login');
  }

  fillCredentials(credentials: any = this.credentials) {
    element(by.css('[placeholder="Login"]')).sendKeys(credentials.username);
    element(by.css('[placeholder="Password"]')).sendKeys(credentials.password);
    this.getButton().click();
  }

  getErrorMessage() {
    return element(by.css('.warn')).getText();
  }

  getButton() {
      return element(by.tagName('button'));
  }
}
