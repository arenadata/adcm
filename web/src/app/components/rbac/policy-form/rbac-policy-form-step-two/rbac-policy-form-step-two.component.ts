import { Component, forwardRef, Input, OnInit } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { AbstractControl, FormGroup } from '@angular/forms';
import { AdwpStringHandler, Entity } from '@app/adwp';
import {
  IRbacObjectCandidateHostModel,
  IRbacObjectCandidateModel,
  IRbacObjectCandidateProviderModel
} from '../../../../models/rbac/rbac-object-candidate';
import { ADD_SERVICE_PROVIDER } from '../../../../shared/add-component/add-service-model';
import { RbacObjectCandidateService } from '../../../../services/rbac-object-candidate.service';
import { filter, startWith, switchMap } from 'rxjs/operators';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';


@Component({
  selector: 'app-rbac-policy-form-step-two',
  templateUrl: './rbac-policy-form-step-two.component.html',
  styleUrls: ['./rbac-policy-form-step-two.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacObjectCandidateService) }
  ],
})
export class RbacPolicyFormStepTwoComponent extends BaseFormDirective implements OnInit {
  @Input()
  form: FormGroup;

  get roleControl(): AbstractControl | null {
    return this.form.parent?.get([0])?.get('role');
  }

  get role(): RbacRoleModel | null {
    return this.roleControl?.value;
  }

  get object(): FormGroup | null {
    return this.form.controls['object'] as FormGroup;
  }

  providerHandler: AdwpStringHandler<IRbacObjectCandidateProviderModel> = (service: IRbacObjectCandidateProviderModel) => service.name;
  hostHandler: AdwpStringHandler<IRbacObjectCandidateHostModel> = (service: IRbacObjectCandidateHostModel) => service.name;

  candidates: IRbacObjectCandidateModel | null = null;

  ngOnInit(): void {
    this.roleControl.valueChanges.pipe(
      startWith(this.role),
      filter((v) => !!v),
      switchMap((role) => this.service.get<IRbacObjectCandidateModel>(role.id)),
      this.takeUntil()
    ).subscribe((candidates: IRbacObjectCandidateModel) => {
      this.candidates = candidates;

      // Set service & parents values
      const selectedService = this.object.get('service')?.value;
      const serviceCandidate = candidates.service.find((s) => selectedService?.name === s?.name);
      const selectedParents: (Pick<Entity, 'id'>)[] | null = this.object.get('parent')?.value;
      const selectedClusters = selectedParents && selectedParents.map((item: Pick<Entity, 'id'>) => {
        return serviceCandidate && serviceCandidate.clusters.find((cluster) => cluster.id === item.id);
      }).filter(Boolean);

      if (selectedService && serviceCandidate && selectedClusters) {
        this.object.get('service').setValue(serviceCandidate);
        this.object.get('parent').setValue(selectedClusters);
      }
    });
  }

  reset(value: any): void {
    if (!this.object) {
      return;
    }

    if (this.object.disabled) {
      this.object.enable();
    }

    this.object.reset(value);
  }
}
