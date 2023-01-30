import { NgZone } from '@angular/core';
import { MonoTypeOperatorFunction, Observable } from 'rxjs';

export function adwpZonefree<T>(ngZone: NgZone): MonoTypeOperatorFunction<T> {
  return source =>
    new Observable(subscriber =>
      ngZone.runOutsideAngular(() => source.subscribe(subscriber)),
    );
}
