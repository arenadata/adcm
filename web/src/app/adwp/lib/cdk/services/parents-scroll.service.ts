import { ElementRef, Inject, Injectable } from '@angular/core';
import { WINDOW } from '@ng-web-apis/common';
import { defer, merge, Observable } from 'rxjs';
import { typedFromEvent } from '../observables';


@Injectable()
export class AdwpParentsScrollService extends Observable<Event> {
  private readonly callback$: Observable<Event>;

  constructor(
    @Inject(ElementRef) { nativeElement }: ElementRef<Element>,
    @Inject(WINDOW) windowRef: any,
  ) {
    super(subscriber => this.callback$.subscribe(subscriber));

    this.callback$ = defer(() => {
      const eventTargets: Array<Element | Window> = [windowRef, nativeElement];

      while (nativeElement.parentElement) {
        nativeElement = nativeElement.parentElement;
        eventTargets.push(nativeElement);
      }

      return merge<Event>(
        ...eventTargets.map<Observable<Event>>(element =>
          typedFromEvent(element, 'scroll'),
        ),
      );
    });
  }
}
