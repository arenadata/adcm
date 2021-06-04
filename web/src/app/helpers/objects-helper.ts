import { JobObject, JobType } from '../core/types';

export class ObjectsHelper {

  static getObject(objects: JobObject[], type: JobType): JobObject {
    return objects.find(object => object.type === type);
  }

}
