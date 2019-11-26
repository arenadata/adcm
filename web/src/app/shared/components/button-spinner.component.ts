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
import { Component, Input, EventEmitter, Output } from '@angular/core';
import { ThemePalette } from '@angular/material/core';

@Component({
  selector: 'app-button-spinner',
  template: `<button mat-raised-button 
  [color]="color"
  [disabled]="disabled"
  (mousedown)="send()"
  (keyup.enter)="send()">
    <mat-spinner diameter="24" class="spinner" *ngIf="_showSpinner"></mat-spinner>
    {{ title }}
</button>`,
  styles: ['.spinner {position: relative; bottom: 5px; display: inline; }'],
})
export class ButtonSpinnerComponent {
  @Input() title: string;
  @Input() color: ThemePalette;
  @Input() disabled: boolean;
  @Input()
  set spinner(flag) {
    this._showSpinner = flag;
  }
  @Output() clickHandler = new EventEmitter();

  _showSpinner = false;
  private _timer: any;

  send() {
    this.showSpinner();
    this.clickHandler.emit(this);    
    this._timer = setTimeout(() => this.hideSpinner(), 5000);
  }

  public hideSpinner() {
    this.disabled = false;
    this._showSpinner = false;
    clearTimeout(this._timer);
  }

  public showSpinner() {
    this.disabled = true;
    this._showSpinner = true;
  }
}
