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
import { Component, EventEmitter, OnInit, ViewChild } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IButton, Widget } from '@app/core/types';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { environment } from '@env/environment';
import { Observable } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { ChannelService } from '../channel.service';

@Component({
  selector: 'app-stack-widget',
  template: `
    <div *ngIf="list$ | async as list" style="min-height: 60px;">
      <mat-nav-list>
        <mat-list-item *ngFor="let ban of list">
          <span>{{ ban.name }} {{ ban.version }}</span>
        </mat-list-item>
      </mat-nav-list>

      <i *ngIf="list.length === 0">Upload a bundle.</i>
    </div>

    <button mat-icon-button matTooltip="To view list bundles" (click)="_action({ type: 'link', name: 'stack' })">
      <mat-icon>view_list</mat-icon>
    </button>
    <button mat-icon-button color="accent" (click)="_addFile()"><mat-icon>save_alt</mat-icon></button>
    <input
      type="file"
      #fileUploadInput
      value="upload_bundle_file"
      (change)="_fileUploadHandler($event.target)"
      style="display: none;"
    />
  `,
})
export class StackComponent implements OnInit, DynamicComponent {
  event = new EventEmitter<DynamicEvent>();
  model?: Widget;

  list$: Observable<any>;
  @ViewChild('fileUploadInput', { static: false }) fileUploadInput;

  constructor(private api: ApiService, private channel: ChannelService) {}

  ngOnInit() {
    this.list$ = this.api.get(`${environment.apiRoot}stack/bundle/`);
  }

  _action(b: IButton) {
    this.event.emit({ name: b.name, data: b });
  }

  _addFile() {
    this.fileUploadInput.nativeElement.click();
  }

  _fileUploadHandler(fu: HTMLInputElement) {
    const file = fu.files.item(0);

    const form = new FormData();
    form.append('file', file, file.name);

    this.api
      .post(`${environment.apiRoot}stack/upload/`, form)
      .pipe(switchMap(() => this.api.post(`${environment.apiRoot}stack/load/`, { bundle_file: file.name })))
      .subscribe(() => {
        this.channel.emmitData({ cmd: 'stack_added', row: null });
        fu.value = '';
        this.list$ = this.api.get(`${environment.apiRoot}stack/bundle/`);
      });
  }
}
