import { Component } from '@angular/core';

@Component({
  selector: 'adwp-loading',
  template: `
    <mat-spinner [diameter]="40" color="accent"></mat-spinner>
    <p>Loading...</p>
  `,
  styles: [`
    :host {
      display: flex;
      justify-content: center;
      align-items: center;
      font-weight: bold;
      font-size: larger;
    }

    mat-spinner {
      margin-right: 7px;
    }

    p {
      margin:  0 0 0 7px;
    }
  `],
})
export class LoadingComponent {}
