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
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ThemePalette } from '@angular/material/core';
import { Router } from '@angular/router';
import { Message, MessageService } from '@app/core';
import { SocketState } from '@app/core/store';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-messenger',
  templateUrl: './messenger.component.html',
  styleUrls: ['./messenger.component.scss'],
})
export class MessengerComponent implements OnInit {
  messages$: Observable<Message[]>;

  @Input()
  expanded = false;
  @Output()
  hide: EventEmitter<any> = new EventEmitter<boolean>();
  @Output()
  onerror: EventEmitter<string> = new EventEmitter();

  constructor(private router: Router, private message: MessageService, private socketStore: Store<SocketState>) {}

  ngOnInit() {
    const s = new Map<string, ThemePalette>([['failed', 'warn'], ['success', 'accent']]);

    // this.socketStore.select(getMessage).subscribe((message: SocketMessage) => {
    //   if (message && message.type === 'job') {
    //     // const flag = localStorage.getItem('notify_ishide');
    //     // if (!flag) {
    //     //   this.expanded = true;
    //     //   this.hide.emit(false);
    //     // }

    //     // this.message.add({
    //     //   id: `${message.type}_${message.id}`,
    //     //   date: new Date(),
    //     //   title: `Run action type : ${message.type} [ ${message.id} ]`,
    //     //   subtitle: `Status : ${message.status}`,
    //     //   kind: s.get(message.status) || 'primary',
    //     //   link: [message.type, message.id],
    //     // });
    //   }
    // });

    this.messages$ = this.message.history$;
  }

  goToLink(link: any[]) {
    this.expanded = false;
    this.router.navigate(link);
  }

  showInfo() {}

  trackByMessages(message: Message) {
    return message.id;
  }

  onHide() {
    this.expanded = false;
    this.hide.emit(true);
    localStorage.setItem('notify_ishide', '1');
  }

  clear(message) {
    this.message.clear(message);
  }

  cleanAll() {
    this.message.clear();
    this.onHide();
  }
}
