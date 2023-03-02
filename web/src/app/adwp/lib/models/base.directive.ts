import {Directive, OnDestroy} from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { MonoTypeOperatorFunction } from 'rxjs';

@Directive()
export class BaseDirective implements OnDestroy {
  destroy$ = new Subject();

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  takeUntil<T>(): MonoTypeOperatorFunction<T> {
    return takeUntil<T>(this.destroy$);
  }

}
