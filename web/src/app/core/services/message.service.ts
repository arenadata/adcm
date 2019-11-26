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
import { Subject } from 'rxjs';
import { ThemePalette } from '@angular/material/core';
import { Injectable } from '@angular/core';

export interface Message {
  id: string;
  title: string;
  date: Date;
  kind?: ThemePalette;
  position?: number;
  subtitle?: string;
  link?: any[];
  information?: string;
}

@Injectable({
  providedIn: 'root',
})
export class MessageService {
  private _history: Message[] = [];
  private _counter = 0;

  public history$ = new Subject<Message[]>();

  private messageSource = new Subject<Partial<Message>>();
  public message$ = this.messageSource.asObservable();

  ignoreMessage = false;

  errorMessage(error: { title: string; subtitle?: string }) {
    if (!this.ignoreMessage) this.messageSource.next({ ...error, id: Date.now().toString(), date: new Date(), kind: 'warn' });
  }

  add(options: Message) {
    if (options.id) {
      const ex = this.findById(options.id);
      if (ex) {
        ex.title = options.title;
        ex.subtitle = options.subtitle ? options.subtitle : ex.subtitle;
        ex.kind = options.kind ? options.kind : ex.kind;
        ex.date = new Date();
      } else this.newMessage(options);
    } else this.newMessage(options);
    this.sort();
  }

  sort() {
    this._history.sort((a, b) => b.date.valueOf() - a.date.valueOf());
  }

  findById(id: string): Message {
    return this._history.find(m => m.id === id);
  }

  private newMessage(message: Message) {
    this._counter++;
    if (!message.id) message.id = Date.now().toString();
    message.position = this._counter;

    this._history.push(message);
    this.history$.next(this._history);
  }

  clear(message?: Message) {
    if (message) {
      this._history = this._history.filter(m => m !== message);
      this.sort();
      this.history$.next(this._history.reverse());
    } else {
      this._history = [];
      this.history$.next(this._history);
    }
  }
}
