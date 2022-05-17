import { Component, Inject } from '@angular/core';
import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';

@Component({
  selector: 'app-snack-bar',
  template: `
    <div class="snack-bar-container">
      <div class="message-wrapper">
        <div class="message">{{ data?.message }}</div>
        <div class="args" *ngIf="data?.args">
          <span class="chip">args</span>
          {{ data?.args }}
        </div>
      </div>
      <button mat-button (click)="snackBarRef.dismiss()">Hide</button>
    </div>
  `,
  styles: [`
    .snack-bar-container {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 14px;
      line-height: 20px;
    }
    .message-wrapper {
      margin-right: 16px;
    }
    .args {
      border-top: 1px solid #78909c;
      margin-top: 7px;
      padding-top: 7px;
    }
    .chip {
      background: #78909c;
      color: #fff;
      padding: 1px 3px;
      border-radius: 3px;
    }
  `]
})
export class SnackBarComponent {

  constructor(
    public snackBarRef: MatSnackBarRef<SnackBarComponent>,
    @Inject(MAT_SNACK_BAR_DATA) public data: {
      message: string,
      args: string;
    },
  ) { }

}
