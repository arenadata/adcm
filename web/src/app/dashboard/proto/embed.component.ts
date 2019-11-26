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
import { Component, OnInit, Input, EventEmitter, Output } from '@angular/core';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';

@Component({
  selector: 'app-embed',
  template: `<div [ngSwitch]="model?.type">
  <ng-template [ngSwitchCase]="'image'">
    <img mat-card-image [src]="model.src" alt="" [style.margin-top.px]="0" />
  </ng-template>
  <ng-template [ngSwitchCase]="'iframe'">
    <iframe mat-card-image [style.margin-top.px]="0" [src]="dangerousUrl" width="100%" height="300" frameborder="0"></iframe>
  </ng-template>
  <ng-template ngSwitchDefault>
    <mat-card-content [innerHTML]="model.html"></mat-card-content>
  </ng-template>    
</div>`,
})
export class EmbedComponent implements OnInit, DynamicComponent {
  @Output() event = new EventEmitter<DynamicEvent>();
  @Input() model?: any;

  dangerousUrl: SafeUrl;
  constructor(private sanitizer: DomSanitizer) {}

  ngOnInit() {
    if (this.model.type === 'iframe') this.dangerousUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.model.src);
  }
}
