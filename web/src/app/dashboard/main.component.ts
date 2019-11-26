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
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { getProfile, ProfileService, ProfileState, saveDashboard } from '@app/core/store';
import { Widget } from '@app/core/types';
import { BaseDirective, DialogComponent } from '@app/shared';
import { DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { Store } from '@ngrx/store';

import { AddComponent } from './add/add.component';
import { UpdateComponent } from './update/update.component';

// import { ToolbarService } from '@app/core';
interface AddData {
  basic: FormGroup;
  type: FormGroup;
}

@Component({
  selector: 'app-main',
  template: '',
  styleUrls: ['./main.component.scss'],
  providers: [ProfileService],
})
export class MainComponent extends BaseDirective implements OnInit, OnDestroy {
  editMode = false;
  introWidget: Widget;
  dashboard: any[];

  constructor(private dialog: MatDialog, private store: Store<ProfileState>, private formBuilder: FormBuilder) {
    super();
  }

  ngOnInit() {
    this.store
      .select(getProfile)
      .pipe(this.takeUntil())
      .subscribe(data => (this.dashboard = data.dashboard));

    // this.tools.controls$.pipe(takeUntil(this.destroy$)).subscribe(e => {
    //   switch (e.cmd) {
    //     case 'switchMode':
    //       this.editMode = e.options.editMode;
    //       break;
    //     case 'showAddWidget':
    //       this._showAddForm();
    //       break;
    //   }
    // });
  }

  drop() {
    this.store.dispatch(saveDashboard({ dashboard: this.dashboard }));
  }

  _clearWidget(widget: Widget, row: number, col: number) {
    if (row !== 3) this.dashboard[row][col] = this.dashboard[row][col].filter(w => w.id !== widget.id);
    else this.dashboard[3] = this.dashboard[3].filter(w => w.id !== widget.id);

    this.store.dispatch(saveDashboard({ dashboard: this.dashboard }));
  }

  _updateWidget(widget: Widget) {
    let form = this.formBuilder.group({
      title: [widget.title, Validators.required],
      height: [widget.height],
    });
    const dialogRef = this.dialog.open(DialogComponent, {
      width: '400px',
      data: { title: 'Update Widget', controls: ['Save', 'Cancel'], component: UpdateComponent, model: form },
    });

    dialogRef.beforeClosed().subscribe(flag => {
      if (flag && form.valid) {
        Object.keys(widget).forEach(k => {
          if (form.contains(k)) widget[k] = form.get(k).value;
        });
        this.store.dispatch(saveDashboard({ dashboard: this.dashboard }));
      }
    });
  }

  _showAddForm() {
    const dialogRef = this.dialog.open(DialogComponent, {
      width: '660px',
      data: { title: 'Add Widget', component: AddComponent },
    });
    dialogRef.beforeClosed().subscribe(e => this._addWidget(e));
  }

  _addWidget(e: DynamicEvent) {
    if (e && e.name === 'add') {
      const data = e.data as AddData,
        row = data.basic.get('width').value,
        col = 0;

      let a = this.dashboard[+row][col].length;
      let widget: Widget = data.basic.value;
      widget.type = data.type.value.type;
      widget.id = ++a;

      if (data.type.value.type === 'intro') {
        this.dashboard[3].push(widget);
      } else this.dashboard[+row][col].push(widget);

      this.store.dispatch(saveDashboard({ dashboard: this.dashboard }));
    }
  }
}
