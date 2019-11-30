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
import { Component, ElementRef, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { CanColor } from '@angular/material/core';

@Component({
  selector: 'app-button-uploader',
  template: `
    <button *ngIf="!asIcon" mat-raised-button [color]="color" (click)="show()"><mat-icon>save_alt</mat-icon> {{ label }}</button>
    <button *ngIf="asIcon" mat-icon-button [color]="color" (click)="show()" [matTooltip]="label"><mat-icon>save_alt</mat-icon></button>
    <input
      type="file"
      #fileUploadInput
      multiple="multiple"
      accept=".tar, .tar.gz, .tgz"
      value="upload_bundle_file"
      style="display: none;"
      (change)="fileUploadHandler($event.target)"
    />
  `
})
export class ButtonUploaderComponent {
  @Input() color: CanColor;
  @Input() label: string;
  @Input() asIcon = false;

  @ViewChild('fileUploadInput', { static: true }) fileUploadInput: ElementRef;

  @Output() output = new EventEmitter<FormData[]>();

  show() {
    this.fileUploadInput.nativeElement.click();
  }

  fileUploadHandler(fu: HTMLInputElement) {
    let output: FormData[] = [];
    for (let i = 0; i < fu.files.length; i++) {
      const file = fu.files.item(i);
      const form = new FormData();
      form.append('file', file, file.name);
      output.push(form);
    }
    this.output.emit(output);
    this.fileUploadInput.nativeElement.value = '';
  }
}
