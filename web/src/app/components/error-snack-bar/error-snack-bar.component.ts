import { Component, Inject } from '@angular/core';
import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';

@Component({
  selector: 'app-error-snack-bar',
  template: `
    <div class="snack-bar-container">
      <div>
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
      justify-content: center;
      align-items: center;
      font-size: 14px;
      line-height: 20px;
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
export class ErrorSnackBarComponent {

  constructor(
    public snackBarRef: MatSnackBarRef<ErrorSnackBarComponent>,
    @Inject(MAT_SNACK_BAR_DATA) public data: {
      message: string,
      args: string;
    },
  ) { }

}
