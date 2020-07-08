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
import { animate, state, style, transition, trigger } from '@angular/animations';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { ChannelService } from '@app/core';
import { EventMessage, SocketState } from '@app/core/store';
import { IActionParameter } from '@app/core/types';
import { Store } from '@ngrx/store';

import { SocketListenerDirective } from '../../directives/socketListener.directive';
import { TakeService } from '../take.service';
import { CompTile, HostTile, Post } from '../types';

@Component({
  selector: 'app-service-host',
  templateUrl: './service-host.component.html',
  styleUrls: ['./service-host.component.scss'],
  animations: [
    trigger('popup', [
      state('show', style({ opacity: 1 })),
      state('hide', style({ opacity: 0 })),
      transition('hide => show', [animate('.2s')]),
      transition('show => hide', [animate('2s')]),
    ]),
  ],
})
export class ServiceHostComponent extends SocketListenerDirective implements OnInit {
  showSpinner = false;
  showPopup = false;
  notify = '';

  serviceComponents: CompTile[];
  hosts: HostTile[];
  form: FormGroup;

  @Input()
  cluster: { id: number; hostcomponent: string };

  /**
   * fixed position buttons for the scrolling
   */
  @Input()
  fixedButton = true;

  /**
   * hide Save button
   */
  @Input()
  hideButton = false;

  @Input()
  actionParameters: IActionParameter[];

  @Output() saveResult = new EventEmitter<Post[]>();

  saveFlag = false;
  initFlag = false;

  scrollEventData: { direct: 1 | -1 | 0; scrollTop: number };

  constructor(public service: TakeService, private channel: ChannelService, socket: Store<SocketState>) {
    super(socket);
  }

  public get noValid() {
    return /*!!this.service.countConstraint */ !this.service.formGroup.valid || !this.service.statePost.data.length;
  }

  ngOnInit() {
    this.init();
    super.startListenSocket();

    this.channel
      .on('scroll')
      .pipe(this.takeUntil())
      .subscribe((e) => (this.scrollEventData = e));
  }

  socketListener(m: EventMessage) {
    if (
      ((m.event === 'change_hostcomponentmap' || m.event === 'change_state') && m.object.type === 'cluster' && m.object.id === this.cluster.id && !this.saveFlag) ||
      ((m.event === 'add' || m.event === 'remove') && m.object.details.type === 'cluster' && +m.object.details.value === this.cluster.id)
    )
      this.init();
  }

  init() {
    if (this.cluster) {
      if (this.initFlag) return;
      this.initFlag = true;
      this.service
        .initSource(this.cluster.hostcomponent, this.actionParameters)
        .pipe(this.takeUntil())
        .subscribe((a) => {
          if (a.hc) this.initFlag = false;
          this.serviceComponents = this.service.Components;
          this.hosts = this.service.Hosts;
          this.form = this.service.formGroup;
        });
    }
  }

  clearServiceFromHost(data: { rel: CompTile; model: HostTile }) {
    this.service.clearServiceFromHost(data);
  }

  clearHostFromService(data: { rel: HostTile; model: CompTile }) {
    this.service.clearHostFromService(data);
  }

  selectHost(host: HostTile) {
    this.service.takeHost(host);
  }

  selectService(comp: CompTile) {
    this.service.takeComponent(comp);
  }

  save() {
    this.saveFlag = true;
    const { id, hostcomponent } = this.cluster;
    this.service.saveSource(id, hostcomponent).subscribe((data) => {
      this.saveResult.emit(data);
      this.notify = 'Settings saved.';
      this.showPopup = true;
      setTimeout(() => (this.showPopup = false), 2000);
      this.saveFlag = false;
    });
  }

  restore() {
    this.service.restore();
  }
}
