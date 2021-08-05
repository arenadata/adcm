import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '@app/core/auth/auth.guard';
import { DetailComponent } from '@app/shared/details/detail.component';
import { MainInfoComponent } from '@app/shared/components';
import { ConfigGroupListComponent } from './pages/group-list/group-list.component';

const routes: Routes = [
  {
    path: '',
    component: ConfigGroupListComponent,
    canActivate: [AuthGuard],
  },
  {
    path: ':configgroup',
    component: DetailComponent,
    canActivate: [AuthGuard],
    canActivateChild: [AuthGuard],
    children: [
      { path: '', redirectTo: 'main', pathMatch: 'full' },
      { path: 'main', component: MainInfoComponent },
      // ToDo hosts from config group
      // { path: 'host', component: ConfigGroupHostComponent },
      // ToDo Config from config group
      // { path: 'config', component: ConfigGroupConfigComponent },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ConfigGroupRoutingModule {
}
