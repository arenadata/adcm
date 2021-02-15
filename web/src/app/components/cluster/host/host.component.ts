import { Component } from '@angular/core';

@Component({
  selector: 'app-cluster-host',
  template: `
    <app-add-button [name]="'host2cluster'" class="add-button">Add hosts</app-add-button>
    <app-list class="main" [type]="'host2cluster'"></app-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:fixed; right: 20px;top:120px;}'],
})
export class HostComponent {}
