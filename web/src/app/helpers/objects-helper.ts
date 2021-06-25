import { JobObject, JobType } from '../core/types';

export class ObjectsHelper {

  static getObject(objects: JobObject[], type: JobType): JobObject {
    return objects.find(object => object.type === type);
  }

  static getObjectUrl(object: JobObject, objects: JobObject[]): string[] {
    if (object.type === 'cluster' || !ObjectsHelper.getCluster(objects)) {
      return ['/', object.type, `${object.id}`];
    } else if (object.type === 'component' && ObjectsHelper.getService(objects)) {
      return ['/', 'cluster', `${ObjectsHelper.getCluster(objects).id}`, 'service', `${ObjectsHelper.getService(objects).id}`, object.type, `${object.id}`];
    } else {
      return ['/', 'cluster', `${ObjectsHelper.getCluster(objects).id}`, object.type, `${object.id}`];
    }
  }

  static sortObjects(objects: JobObject[]): JobObject[] {
    return [
      ObjectsHelper.getObject(objects, 'host'),
      ObjectsHelper.getObject(objects, 'provider'),
      ObjectsHelper.getObject(objects, 'component'),
      ObjectsHelper.getObject(objects, 'service'),
      ObjectsHelper.getObject(objects, 'cluster'),
    ].filter(Boolean);
  }

  static getCluster(objects: JobObject[]): JobObject {
    return ObjectsHelper.getObject(objects, 'cluster');
  }

  static getService(objects: JobObject[]): JobObject {
    return ObjectsHelper.getObject(objects, 'service');
  }

}
