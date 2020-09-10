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
import { fromEvent } from 'rxjs';
import { debounceTime, tap } from 'rxjs/operators';

import { BaseDirective } from '../../directives/base.directive';

@Component({
  selector: 'app-actions',
  template: `
    <div #wrap>
      <button
        tabindex="-1"
        *ngFor="let action of actions"
        #button
        mat-stroked-button
        color="warn"
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
        tabindex="-1"
        mat-stroked-button
        color="warn"
        class="menu-more-action"
        *ngFor="let a of forMenu"
        [appForTest]="'action_btn'"
        [disabled]="isIssue"
        [appActions]="{ cluster: cluster, actions: [a] }"
      >
        {{ a.display_name }}
      </button>
    </mat-menu>
  `,
  styleUrls: ['./actions.component.scss'],
})
export class ActionsComponent extends BaseDirective implements OnInit, AfterViewChecked {
  actions: IAction[] = [];

  @Input() isIssue: boolean;
  @Input() cluster: { id: number; hostcomponent: string };
  @Input() set source(actions: IAction[]) {
    this.actions = actions;
    if (!actions.length) this.render.setStyle(this.more.nativeElement, 'display', 'none');
  }

  stateButtons = 0;
  forMenu: IAction[] = [];

  @ViewChild('wrap', { read: ElementRef, static: true }) wrap: ElementRef;
  @ViewChild('more', { read: ElementRef, static: true }) more: ElementRef;
  @ViewChildren('button', { read: ElementRef }) buttons: QueryList<ElementRef>;
  @ViewChild(MatMenuTrigger, { static: true }) trigger: MatMenuTrigger;

  constructor(private render: Renderer2, private el: ElementRef) {
    super();
  }

  ngOnInit() {
    fromEvent(window, 'resize')
      .pipe(
        this.takeUntil(),
        tap(() => this.trigger.closeMenu()),
        debounceTime(500)
      )
      .subscribe(() => this.onresize());
  }

  ngAfterViewChecked(): void {
    if (this.stateButtons !== this.buttons.length) {
      this.stateButtons = this.buttons.length;
      setTimeout(() => this.onresize(), 0);
    }
  }

  onresize() {
    const bw = this.buttons.map<number>((b) => b.nativeElement.offsetWidth + 10);
    const elWidth = +this.el.nativeElement.clientWidth - 50;
    const dw = this.calcWidth(elWidth, bw);
    //
    this.forMenu = this.actions.slice(dw[0]);
    this.render.setStyle(this.wrap.nativeElement, 'width', `${dw[1]}px`);
    this.render.setStyle(this.more.nativeElement, 'display', dw[2] ? 'block' : 'none');
  }

  calcWidth(w: number, bw: number[]): [number, number, boolean] {
    return bw.reduce((p, c, i) => (p[2] || p[1] + c > w ? [p[0], p[1], true] : [i + 1, p[1] + c, false]), [0, 0, false]);
  }
}
