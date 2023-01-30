import { EventEmitter, Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ComponentData {
  path: string;
  model: any;
  emitter: EventEmitter<any>;
}
