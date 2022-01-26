import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { LogComponent } from '@app/ws-logs/log.component';
import { AuthGuard } from '@app/core/auth/auth.guard';
import { LoginComponent } from '@app/main/login/login.component';
import { ProfileComponent } from '@app/main/profile/profile.component';
import { SupportComponent } from '@app/main/support/support.component';
import { FatalErrorComponent, ForbiddenComponent, GatewayTimeoutComponent, PageNotFoundComponent } from '@app/main/server-status.component';
import { HostListComponent } from '@app/components/host/host-list/host-list.component';
import { MainInfoComponent } from '@app/shared/components';
import { ConfigComponent } from '@app/shared/configuration/main/config.component';
import { HostproviderComponent } from '@app/components/hostprovider/hostprovider.component';
import { ConfigGroupHostListComponent, ConfigGroupListComponent } from '@app/config-groups';
import { HostDetailsComponent } from '@app/components/host/host-details/host-details.component';
import { ProviderDetailsComponent } from '@app/components/hostprovider/provider-details/provider-details.component';
import { GroupConfigDetailsComponent } from '@app/components/hostprovider/group-config-details/group-config-details.component';
import { HostStatusComponent } from '@app/components/host/host-status/host-status.component';

const routes: Routes = [
  {
    path: 'cluster',
    loadChildren: () => import('app/entry/cluster/cluster.module').then(m => m.ClusterModule),
  },
  {
    path: 'job',
    loadChildren: () => import('app/entry/job/job.module').then(m => m.JobModule),
  },
  {
    path: 'task',
    loadChildren: () => import('app/entry/task/task.module').then(m => m.TaskModule),
  },
  {
    path: 'bundle',
    loadChildren: () => import('app/entry/bundle/bundle.module').then(m => m.BundleModule),
  },
  {
    path: 'host',
    children: [
      {
        path: '',
        pathMatch: 'full',
        component: HostListComponent,
      }, {
        path: ':host',
        component: HostDetailsComponent,
        children: [
          { path: '', redirectTo: 'main', pathMatch: 'full' },
          { path: 'main', component: MainInfoComponent },
          { path: 'config', component: ConfigComponent },
          { path: 'status', component: HostStatusComponent },
        ],
      }
    ],
    canActivate: [AuthGuard],
  },
  {
    path: 'provider',
    children: [
      {
        path: '',
        pathMatch: 'full',
        component: HostproviderComponent,
      }, {
        path: ':provider',
        component: ProviderDetailsComponent,
        children: [
          { path: '', redirectTo: 'main', pathMatch: 'full' },
          { path: 'main', component: MainInfoComponent },
          { path: 'config', component: ConfigComponent },
          { path: 'group_config', component: ConfigGroupListComponent },
        ]
      }
    ],
    canActivate: [AuthGuard],
  },
  {
    path: 'provider/:provider/group_config/:group_config',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: GroupConfigDetailsComponent,
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },

  {
    path: 'cluster/:cluster/host/:host/provider/:provider',
    redirectTo: 'provider/:provider',
  },
  {
    path: 'host/:host/provider/:provider',
    redirectTo: 'provider/:provider',
  },
  { path: '', redirectTo: 'admin', pathMatch: 'full' },
  { path: 'log', component: LogComponent, canActivate: [AuthGuard] },
  { path: 'login', component: LoginComponent },
  { path: 'profile', component: ProfileComponent, canActivate: [AuthGuard] },
  { path: 'support', component: SupportComponent },
  { path: '403', component: ForbiddenComponent },
  { path: '404', component: PageNotFoundComponent },
  { path: '500', component: FatalErrorComponent },
  { path: '504', component: GatewayTimeoutComponent },
  {
    path: 'admin',
    loadChildren: () => import('app/admin/admin.module').then(m => m.AdminModule),
  },
  { path: '**', component: PageNotFoundComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { relativeLinkResolution: 'legacy' })],
  exports: [RouterModule]
})
export class AppRoutingModule {
}
