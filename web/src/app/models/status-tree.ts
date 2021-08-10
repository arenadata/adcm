export enum SubjectStatus {
  Success,
  Fail,
}

export interface StatusTreeSubject {
  name: string;
  status: SubjectStatus;
}

export interface StatusTree {
  subject: StatusTreeSubject;
  children: StatusTree[];
}
