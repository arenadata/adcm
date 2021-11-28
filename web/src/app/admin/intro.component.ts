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
import { FormControl, FormGroup } from '@angular/forms';

@Component({
  selector: 'app-intro',
  templateUrl: 'intro.component.html',
  styles: [':host {padding: 0 10px;}', '.admin-warn {border:solid 1px #ff9800;margin-right: 20px;}', '.admin-warn ul li {padding: 8px 0;}'],
})
export class IntroComponent {
  adcm_url = `${location.protocol}//${location.host}`;


  options = ['group1', 'group2', 'group3', 'group4'];

  form: FormGroup = new FormGroup({
    group: new FormControl(['group2'])
  });

  constructor() {
    this.form.valueChanges.subscribe((v) => {
      console.log('change: ', v);
    });
  }
}
