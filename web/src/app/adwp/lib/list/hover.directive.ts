
import { Directive, ElementRef, HostListener } from '@angular/core';


@Directive({
  selector: '[adwpHover]',
})
export class HoverDirective {
  constructor(private el: ElementRef) {}

  @HostListener('mouseenter')
  onmouseenter(): void {
    this.el.nativeElement.style.backgroundColor = 'rgba(255, 255, 255, 0.12)';
    this.el.nativeElement.style.cursor = 'pointer';
  }

  @HostListener('mouseleave')
  onmouseleave(): void {
    this.el.nativeElement.style.backgroundColor = 'transparent';
    this.el.nativeElement.style.cursor = 'defautl';
  }
}
