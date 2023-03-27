// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { BaseEntity } from './api';
import { Entity } from '@app/adwp';

export type JobStatus = 'created' | 'running' | 'failed' | 'success' | 'aborted';

export type JobType = 'component' | 'service' | 'cluster' | 'host' | 'provider';

export interface JobObject {
  id: number;
  name: string;
  type: JobType;
  url?: string[];
}

interface TaskBase extends Entity {
  start_date: string;
  finish_date: string;
  objects: JobObject[];
  status: JobStatus;
  action: JobAction;
  terminatable: boolean;
  cancel: string;
}

export interface JobAction {
  prototype_name?: string;
  prototype_version?: string;
  bundle_id?: number;
  display_name: string;
}
interface JobRaw extends TaskBase {
  log_files: LogFile[];
  start_date: string;
  finish_date: string;
}

export interface TaskRaw extends TaskBase {
  jobs: Job[];
}

export type Job = JobRaw & BaseEntity;
export type Task = TaskRaw & BaseEntity;

export interface LogFile {
  id: number;
  url: string;
  name: string;
  type: string;
  format: 'txt' | 'json';
  download_url: string;
  content: string | CheckLog[];
}

export interface CheckLog {
  title: string;
  message: string;
  result: boolean;
  type: 'group' | 'check';
  content?: CheckLog[];
}
