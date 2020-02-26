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
import { AfterViewChecked, Component, ElementRef, Input, OnInit, QueryList, Renderer2, ViewChild, ViewChildren } from '@angular/core';
import { MatMenuTrigger } from '@angular/material/menu';
import { IAction } from '@app/core/types';
import { fromEvent, Observable } from 'rxjs';
import { debounceTime, tap } from 'rxjs/operators';

import { BaseDirective } from '../../directives/base.directive';

@Component({
  selector: 'app-actions',
  template: `
    <div #wrap>
      <button
        #btn
        mat-raised-button
        color="warn"
        *ngFor="let action of actions$ | async"
        [appForTest]="'action_btn'"
        [disabled]="isIssue"
        [appActions]="{ cluster: cluster, actions: [action] }"
      >
        {{ action.display_name }}
      </button>
    </div>
    <button mat-icon-button [matMenuTriggerFor]="menu" #more class="button-more">
      <mat-icon>more_vert</mat-icon>
    </button>
    <mat-menu #menu="matMenu" class="menu-more">
      <button
        mat-raised-button
        color="warn"
        *ngFor="let a of forMenu"
        [appForTest]="'action_btn'"
        class="menu-more-action"
        [disabled]="isIssue"
        [appActions]="{ cluster: cluster, actions: [a] }"
      >
        {{ a.display_name }}
      </button>
    </mat-menu>
  `,
  styleUrls: ['./actions.component.scss']
})
export class ActionsComponent extends BaseDirective implements OnInit, AfterViewChecked {
  separ = 0;
  @Input() isIssue: boolean;
  @Input() cluster: { id: number; hostcomponent: string };
  actions: IAction[];
  actions$: Observable<IAction[]>;
  @Input() set source(value$: Observable<IAction[]>) {
    this.actions$ = value$.pipe(
      tap(a => {
        this.actions = a;
        if (!a.length) this.render.setStyle(this.more.nativeElement, 'display', 'none');
      }),
      this.takeUntil()
    );
  }

  stateButtons = 0;
  forMenu: IAction[] = [];

  @ViewChild('wrap', { read: ElementRef, static: true }) el: ElementRef;
  @ViewChild('more', { read: ElementRef, static: true }) more: ElementRef;
  @ViewChildren('btn', { read: ElementRef }) buttons: QueryList<ElementRef>;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;

  constructor(private render: Renderer2) {
    super();
  }

  ngOnInit() {
    fromEvent(window, 'resize')
      .pipe(
        tap(() => this.trigger.closeMenu()),
        debounceTime(100),
        this.takeUntil()
      )
      .subscribe(() => this.onresize());
  }

  ngAfterViewChecked(): void {
    if (this.stateButtons !== this.buttons.length) {
      this.stateButtons = this.buttons.length;
      setTimeout(() => this.onresize(), 1);
    }
  }

  onresize() {
    const el = this.el.nativeElement;
    this.render.setStyle(el, 'width', 'auto');

    const dw = this.calcWidth(+this.el.nativeElement.clientWidth);
    this.render.setStyle(el, 'width', dw);

    const w = el.clientWidth,
      sw = el.scrollWidth;
    this.render.setStyle(this.more.nativeElement, 'display', w === 0 || w >= sw ? 'none' : 'block');

    this.forMenu = this.actions.slice(this.separ);
  }

  calcWidth(w: number) {
    let width = 0;
    this.buttons.some((c, i) => {
      const d = width + (c.nativeElement.offsetWidth + 10);
      if (d > w) {
        this.separ = i;
        return true;
      } else width = d;
    });

    return `${width}px`;
  }
}
