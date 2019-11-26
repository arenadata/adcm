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
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';

import { WidgetTypeGroups } from '../proto';

@Component({
  selector: 'app-add',
  templateUrl: './add.component.html',
  styleUrls: ['./add.component.scss'],
})
export class AddComponent implements DynamicComponent, OnInit {
  @Output() event = new EventEmitter<DynamicEvent>();

  isLinear = true;
  firstFormGroup: FormGroup;
  secondFormGroup: FormGroup;

  @Output() addCallbak = new EventEmitter();
  @Output() cancelCallback = new EventEmitter();

  typeGroups = WidgetTypeGroups;

  constructor(private _formBuilder: FormBuilder) {}

  ngOnInit() {
    this.firstFormGroup = this._formBuilder.group({
      title: ['', Validators.required],
      width: ['1', Validators.required],
      height: [''],
    });
    this.secondFormGroup = this._formBuilder.group({
      type: ['', Validators.required],
    });
  }

  _add() {
    this.event.emit({ name: 'add', data: { basic: this.firstFormGroup, type: this.secondFormGroup } });
  }

  _cancel() {
    this.event.emit({ name: 'cancel' });
  }
}
