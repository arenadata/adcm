import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { LogComponent } from '@app/ws-logs/log.component';
import { AuthGuard } from '@app/core/auth/auth.guard';
import { LoginComponent } from '@app/main/login/login.component';
import { ProfileComponent } from '@app/main/profile/profile.component';
import { SupportComponent } from '@app/main/support/support.component';
import { FatalErrorComponent, GatewayTimeoutComponent, PageNotFoundComponent } from '@app/main/server-status.component';
import { HostListComponent } from '@app/components/host-list/host-list.component';
import { DetailComponent } from '@app/shared/details/detail.component';
import { MainInfoComponent, StatusComponent } from '@app/shared/components';
import { ConfigComponent } from '@app/shared/configuration/main/config.component';
import { ActionCardComponent } from '@app/shared/components/actions/action-card/action-card.component';
import { HostproviderComponent } from '@app/components/hostprovider/hostprovider.component';
import { CONFIG_GROUP_LIST_SERVICE, ConfigGroupHostListComponent, ConfigGroupListComponent } from '@app/config-groups';

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
    component: HostListComponent,
    canActivate: [AuthGuard],
  },
  {
    path: 'host/:host',
    component: DetailComponent,
    canActivate: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'status', component: StatusComponent },
      { path: 'action', component: ActionCardComponent },
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
  {
    path: 'provider',
    canActivate: [AuthGuard],
    component: HostproviderComponent,
  },
  {
    path: 'provider/:provider',
    canActivate: [AuthGuard],
    component: DetailComponent,
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      { path: 'config', component: ConfigComponent },
      { path: 'group_configs', component: ConfigGroupListComponent },
      { path: 'action', component: ActionCardComponent },
    ],
  },
  {
    path: 'provider/:provider/group_configs/:group_configs',
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    component: DetailComponent,
    data: {
      entityService: CONFIG_GROUP_LIST_SERVICE
    },
    children: [
      { path: '', redirectTo: 'host', pathMatch: 'full' },
      { path: 'host', component: ConfigGroupHostListComponent },
      { path: 'config', component: ConfigComponent, data: { isGroupConfig: true } },
    ],
  },

  { path: '', redirectTo: 'admin', pathMatch: 'full' },
  { path: 'log', component: LogComponent, canActivate: [AuthGuard] },
  { path: 'login', component: LoginComponent },
  { path: 'profile', component: ProfileComponent, canActivate: [AuthGuard] },
  { path: 'support', component: SupportComponent },
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
