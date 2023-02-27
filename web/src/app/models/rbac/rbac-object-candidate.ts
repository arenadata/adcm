import { Entity } from '@app/adwp';

export interface IRbacObjectCandidateModel {
  cluster: IRbacObjectCandidateClusterModel[];
  parent: IRbacObjectCandidateClusterModel[];
  provider: IRbacObjectCandidateProviderModel[];
  service: IRbacObjectCandidateServiceModel[];
  host: IRbacObjectCandidateHostModel[];
}

export interface IRbacObjectCandidateClusterModel extends Entity {
  name: string;
  type: 'cluster';
}

export interface IRbacObjectCandidateProviderModel extends Entity {
  name: string;
  type: 'provider';
}


export interface IRbacObjectCandidateServiceModel extends Entity {
  name: string;
  type?: 'service',
  clusters: IRbacObjectCandidateClusterModel[];
}

export interface IRbacObjectCandidateHostModel extends Entity {
  name: string;
  type: 'host';
}
