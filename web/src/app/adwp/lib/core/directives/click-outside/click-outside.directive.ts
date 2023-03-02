import { Directive, ElementRef, EventEmitter, HostListener, Output } from '@angular/core';

@Directive({
  selector: '[adwpClickOutside]'
})
export class AdwpClickOutsideDirective {
  constructor(private _elementRef: ElementRef) {
  }

  @Output()
  public adwpClickOutside = new EventEmitter<MouseEvent>();

  @HostListener('document:click', ['$event', '$event.target'])
  public onClick(event: MouseEvent, targetElement: HTMLElement): void {
    if (!targetElement) {
      return;
    }

    const clickedInside = this._elementRef.nativeElement.contains(targetElement);
    if (!clickedInside) {
      this.adwpClickOutside.emit(event);
    }
  }
}
