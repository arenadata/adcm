import { Entity } from '@adwp-ui/widgets';

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
  clusters: IRbacObjectCandidateClusterModel[];
}

export interface IRbacObjectCandidateHostModel extends Entity {
  name: string;
  type: 'host';
}
