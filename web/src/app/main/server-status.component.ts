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
import { Component } from '@angular/core';

const styleCSS = 'div { font-weight:bold; margin: 40px auto; width: 400px;}';

// http 500
@Component({
  styles: [styleCSS],
  template: '<div>Critical error on the server. <p>Contact to <a routerLink="/support">support</a>.</p></div>',
})
export class FatalErrorComponent {}

// http 504
@Component({
  styles: [styleCSS],
  template: '<div>Gateway Timeout.</div>',
})
export class GatewayTimeoutComponent {}

// http 404
@Component({
  styles: [styleCSS],
  template: '<div>Page not found.</div>',
})
export class PageNotFoundComponent {}
