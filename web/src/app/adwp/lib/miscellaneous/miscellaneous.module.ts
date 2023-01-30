import { Inject, InjectionToken, ModuleWithProviders, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

export interface MiscConfig {
  supportUrl: any[] | string;
  homeUrl: any[] | string;
}

export const MiscConfigService = new InjectionToken<MiscConfig>('MiscConfig');

const styleCSS = `
  :host { display: flex; width: 100%; align-items: center; justify-content: center; }
  div { font-weight: bold; text-align: center; font-size: larger; }
`;

// http 500
@Component({
  styles: [styleCSS],
  template: '<div>Critical error on the server. <p>Contact to <a [routerLink]="config.supportUrl">support</a>.</p></div>',
})
export class FatalErrorComponent {

  constructor(
    @Inject(MiscConfigService) public config: MiscConfig,
  ) {}

}

// http 504
@Component({
  styles: [styleCSS],
  template: '<div>Gateway Timeout.</div>',
})
export class GatewayTimeoutComponent {}

// http 404
@Component({
  styles: [styleCSS],
  template: '<div>404<p>Page not found.</p><p>Go to <a [routerLink]="config.homeUrl">home page</a></p></div>',
})
export class PageNotFoundComponent {

  constructor(
    @Inject(MiscConfigService) public config: MiscConfig,
  ) {}

}

@NgModule({
  declarations: [
    FatalErrorComponent,
    GatewayTimeoutComponent,
    PageNotFoundComponent,
  ],
  imports: [
    CommonModule,
    RouterModule,
  ],
  exports: [
    FatalErrorComponent,
    GatewayTimeoutComponent,
    PageNotFoundComponent,
  ],
})
export class AdwpMiscellaneousModule {

  public static forRoot(config: MiscConfig): ModuleWithProviders<AdwpMiscellaneousModule> {
    return {
      ngModule: AdwpMiscellaneousModule,
      providers: [
        {
          provide: MiscConfigService,
          useValue: config,
        }
      ]
    };
  }

}
