export class EventHelper {

  static stopPropagation(event: MouseEvent): void {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }
  }

}
