import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'app-status-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
    >
      <img src="/assets/homer-simpson.png" class="homer">
      <span>{{ label }}</span>
      <mat-icon [color]="odd ? 'warn' : 'accent'">lightbulb</mat-icon>
      <mat-icon [color]="!odd ? 'warn' : 'accent'">star_rate</mat-icon>
    </a>
  `,
  styleUrls: ['./status-menu-item.component.scss']
})
export class StatusMenuItemComponent implements OnInit {

  @Input() label: string;
  @Input() link: string;

  odd = true;

  ngOnInit() {
    setInterval(() => {
      this.odd = !this.odd;
    }, 1000);
  }

}
