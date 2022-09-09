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
import { Component, ComponentFactoryResolver, EventEmitter, Inject, OnInit, Type, ViewChild, HostListener } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { DynamicComponent, DynamicDirective, DynamicEvent } from '@app/shared/directives';
import { ChannelService } from '@app/core/services';
import { keyChannelStrim } from '@app/core/services';
import { ActionParameters } from '@app/shared/components/actions/actions.directive';

export interface DialogData {
  title: string;
  component: Type<DynamicComponent>;
  model?: ActionParameters | any;
  event?: EventEmitter<any>;
  text?: string;
  controls?: any[] | any;
  disabled?: boolean;
}

@Component({
  selector: 'app-dialog',
  template: `
    <h3 mat-dialog-title class="overflow">{{ _title() }}</h3>
    <mat-dialog-content class="content" appScroll (read)="scroll($event)">
      <pre *ngIf="data.text">{{ data.text }}</pre>
      <ng-template appDynamic></ng-template>
    </mat-dialog-content>
    <mat-dialog-actions class="controls" *ngIf="data.controls">
      <ng-container *ngIf="controlsIsArray(); else withLabel">
        <ng-template *ngTemplateOutlet="isArray; context: { buttons: data.controls }"></ng-template>
      </ng-container>
    </mat-dialog-actions>
    <ng-template #withLabel>
      <label class="warn" style="margin-right: 30px;">{{ data.controls.label }}</label>
      <ng-container *ngTemplateOutlet="isArray; context: { buttons: data.controls.buttons }"></ng-container>
    </ng-template>
    <ng-template #isArray let-buttons="buttons">
      <button mat-raised-button color="primary" (click)="_noClick()" tabindex="-1">{{ buttons[1] }}</button>
      <button mat-raised-button color="accent" [mat-dialog-close]="true" [disabled]="data?.disabled" tabindex="2">
        {{ buttons[0] }}
      </button>
    </ng-template>
  `,
  styles: [`
    mat-dialog-content {
      height: 100%;
    }
    pre {
      overflow: hidden;
      white-space: pre-wrap;
      word-break: break-word;
    }
  `],
})
export class DialogComponent implements OnInit {
  controls: string[];
  noClose: boolean | undefined;

  instance: DynamicComponent;

  @ViewChild(DynamicDirective, { static: true }) dynamic: DynamicDirective;

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      const c = this.instance;
      if (c?.onEnterKey) c.onEnterKey();
    }
  }

  constructor(
    public dialogRef: MatDialogRef<DialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private componentFactoryResolever: ComponentFactoryResolver,
    private channel: ChannelService
  ) {}

  controlsIsArray() {
    return Array.isArray(this.data.controls);
  }

  ngOnInit(): void {
    if (this._isTypeLdap() && this._isGroupDialog()) {
      this.data.disabled = true;
    }

    if (this.data.component) {
      const componentFactory = this.componentFactoryResolever.resolveComponentFactory(this.data.component);
      const viewContainerRef = this.dynamic.viewContainerRef;
      viewContainerRef.clear();

      const componentRef = viewContainerRef.createComponent(componentFactory);
      this.instance = <DynamicComponent>componentRef.instance;
      this.instance.model = this.data.model;
      // event define in the component
      if (this.instance.event) this.instance.event.subscribe((e: DynamicEvent) => this.dialogRef.close(e));

      if (this.data.event) this.instance.event = this.data.event;
    }
  }

  scroll(stop: { direct: -1 | 1 | 0; screenTop: number }) {
    this.channel.next(keyChannelStrim.scroll, stop);
  }

  _noClick(): void {
    this.dialogRef.close();
  }

  _isTypeLdap() {
    return this.data?.model?.value?.type === 'ldap'
  }

  _title(): string {
    if (this._isTypeLdap() && this._isGroupDialog()) return 'Group Info';
    if (this._isUserInactive()) return 'User info';
    return this.data.title || 'Notification';
  }

  _isGroupDialog() {
    return this.data.model.name === 'Group';
  }

  _isUserDialog() {
    return this.data.model.name === 'user';
  }

  _isUserInactive() {
    return !this.data?.model?.value?.is_active === false;
  }
}
