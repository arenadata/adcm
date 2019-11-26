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
import { Component, ComponentFactoryResolver, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { Router } from '@angular/router';
import { Widget } from '@app/core/types';
import { DialogComponent } from '@app/shared';
import { DynamicComponent, DynamicDirective, DynamicEvent } from '@app/shared/directives/dynamic.directive';

import { PROTOTYPE_WIDGETS } from '../proto';

@Component({
  selector: 'app-widget',
  templateUrl: './widget.component.html',
  styleUrls: ['./widget.component.scss'],
})
export class WidgetComponent implements OnInit {
  @Input()
  widget: Widget;
  @Input()
  dragEnabled: boolean;

  @Output()
  clearWidget = new EventEmitter();
  @Output()
  updateWidget = new EventEmitter<Widget>();

  @ViewChild(DynamicDirective, { static: false })
  dynamic: DynamicDirective;

  instance: DynamicComponent;

  notify = '';

  constructor(
    private router: Router,
    private dialog: MatDialog,
    private componentFactoryResolever: ComponentFactoryResolver
  ) {}

  ngOnInit(): void {
    const view = PROTOTYPE_WIDGETS[this.widget.type];
    if (view && view.component) {
      let componentFactory = this.componentFactoryResolever.resolveComponentFactory(view.component);
      let viewContainerRef = this.dynamic.viewContainerRef;
      viewContainerRef.clear();

      let componentRef = viewContainerRef.createComponent(componentFactory);
      this.instance = <DynamicComponent>componentRef.instance;
      this.instance.model = view.data || this.widget;
      this.instance.event.subscribe((e: DynamicEvent) => {
        if (e.data && e.data.type === 'link') this.router.navigate(['app', e.data.name]);
      });
    }
  }

  _settingsWidget(widget) {
    this.updateWidget.emit(widget);
  }

  _clearWidget(widget: Widget) {
    const dialogRef = this.dialog.open(DialogComponent, {
      width: '250px',
      data: {
        title: 'Remove widget',
        text: `Widget [ <b>${widget.title}</b> ] will be removed.`,
        controls: ['Yes', 'No'],
      },
    });

    dialogRef.beforeClosed().subscribe(yes => {
      if (yes) {
        this.clearWidget.emit(widget);
      }
    });
  }
}
