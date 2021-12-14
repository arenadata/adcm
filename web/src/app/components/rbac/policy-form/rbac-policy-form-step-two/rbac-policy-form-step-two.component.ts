import { Component, Inject, Input, OnInit } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormArray, FormGroup } from '@angular/forms';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { ADD_SERVICE_PROVIDER, IAddService } from '../../../../shared/add-component/add-service-model';
import { MatDialog } from '@angular/material/dialog';
import { ICluster } from '../../../../models/cluster';
import { Observable } from 'rxjs';
import { map, switchMap, tap } from 'rxjs/operators';
import { ApiService } from '../../../../core/api';
import { Entities } from '../../../../core/types';
import { AdwpStringHandler } from '@adwp-ui/widgets';
import { IClusterService } from '../../../../models/cluster-service';

@Component({
  selector: 'app-rbac-policy-form-step-two',
  templateUrl: './rbac-policy-form-step-two.component.html',
  styleUrls: ['./rbac-policy-form-step-two.component.scss']
})
export class RbacPolicyFormStepTwoComponent extends BaseFormDirective implements OnInit {
  @Input()
  form: FormGroup;

  get role(): RbacRoleModel | null {
    return this.form.parent?.get([0])?.get('role')?.value;
  }

  clusterHandler: AdwpStringHandler<ICluster> = (cluster: ICluster) => cluster.name;
  serviceHandler: AdwpStringHandler<IClusterService> = (service: IClusterService) => service.name;


  clusters$: Observable<ICluster[]>;
  services$: Observable<IClusterService[]>;

  constructor(api: ApiService,
              @Inject(ADD_SERVICE_PROVIDER) service: IAddService,
              dialog: MatDialog,
  ) {
    super(service, dialog);

    this.clusters$ = api.root.pipe(
      switchMap((root) => api.getList<Entities>(root['cluster'], null)),
      map((list) => list as unknown as ICluster[])
    );

    this.services$ = api.root.pipe(
      switchMap((root) => api.getList<Entities>(root['service'], null)),
      tap((aa) => console.log(aa)),
      map((list) => list as unknown as IClusterService[])
    );

  }

  object(type: 'cluster' | 'service'): FormGroup | null {
    const object = this.form.controls['object'] as FormArray;
    if (type === 'cluster') {
      return object.get([0]) as FormGroup;
    }
    if (type === 'service') {
      return object.get([1]) as FormGroup;
    }
    return null;
  }

  ngOnInit(): void {
  }


}
