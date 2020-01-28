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
import { Component, EventEmitter, Input, OnDestroy, Output } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';

import { DialogComponent } from '../components/dialog.component';
import { BaseDirective } from '../directives/base.directive';
import { AddFormComponent as component } from './add-form.component';
import { AddService } from './add.service';

@Component({ 
  selector: 'app-add-button',
  template: `
    <button [appForTest]="'create-btn'" mat-raised-button color="accent" (click)="showForm()">
      <mat-icon>library_add</mat-icon>&nbsp;<ng-content></ng-content>
    </button>
  `,
  styles: ['button {margin-right: 6px;}'],
})
export class AddButtonComponent extends BaseDirective implements OnDestroy {
  @Input() name: string;
  @Output() added = new EventEmitter();

  constructor(private dialog: MatDialog, private service: AddService) {
    super();
  }

  showForm() {
    const model = this.service.model(this.name);
    model.success = new EventEmitter();
    model.success.pipe(this.takeUntil()).subscribe(() => this.hideForm());

    this.dialog.open(DialogComponent, {
      data: {
        title: `Add ${model.title || model.name}`,
        component,
        model,
      },
    });
  }

  hideForm() {
    this.dialog.closeAll();
  }
}
