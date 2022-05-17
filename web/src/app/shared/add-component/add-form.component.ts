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
import { AfterViewInit, Component, ComponentFactoryResolver, ViewChild, ViewContainerRef } from '@angular/core';

import { ChannelService, keyChannelStrim } from '@app/core/services';
import { DynamicComponent, DynamicDirective } from '@app/shared/directives';
import { BaseFormDirective } from './base-form.directive';
import { FormModel } from '@app/shared/add-component/add-service-model';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';

@Component({
  selector: 'app-add-form',
  template: `
    <div [style.minWidth.px]="450">
      <ng-container appDynamic [ngSwitch]="model.name">
        <ng-container *ngSwitchCase="'provider'">
          <app-add-provider #cc></app-add-provider>
        </ng-container>
        <ng-container *ngSwitchCase="'host'">
          <app-add-host (event)="message($event)" #cc></app-add-host>
        </ng-container>
        <ng-container *ngSwitchCase="'cluster'">
          <app-add-cluster #cc></app-add-cluster>
        </ng-container>
        <ng-container *ngSwitchCase="'service'">
          <app-add-service #cc></app-add-service>
        </ng-container>
        <ng-container *ngSwitchCase="'host2cluster'">
          <app-add-host2cluster (event)="message($event)" #cc></app-add-host2cluster>
        </ng-container>
      </ng-container>
    </div>
  `,
})
export class AddFormComponent implements DynamicComponent, AfterViewInit {
  model: FormModel;

  instance: BaseFormDirective;

  constructor(
    private channel: ChannelService,
    public viewContainer: ViewContainerRef,
    private componentFactoryResolver: ComponentFactoryResolver
  ) {}

  @ViewChild('cc') container: BaseFormDirective;

  @ViewChild(DynamicDirective, { static: true }) dynamic: DynamicDirective;

  onEnterKey(): void {
    if (this.container) {
      if (this.container.form.valid) this.container.save();
    }
  }

  message(m: string): void {
    this.channel.next(keyChannelStrim.notifying, m);
  }

  ngAfterViewInit(): void {
    if (this.model.component) {
      const componentFactory = this.componentFactoryResolver.resolveComponentFactory(this.model.component);
      const viewContainerRef = this.dynamic.viewContainerRef;
      viewContainerRef.clear();

      const componentRef = viewContainerRef.createComponent(componentFactory);
      this.instance = componentRef.instance;
      if (this.instance instanceof RbacFormDirective) {
        this.instance.value = this.model.value;
      }
    }
  }

}
