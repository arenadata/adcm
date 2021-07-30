from haystack import indexes
from cm.models import Cluster, Prototype


class PrototypeIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    type = indexes.CharField(model_attr='type')
    bundle = indexes.CharField(model_attr='bundle')

    def get_model(self):
        return Prototype
    
    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()
        

class ClusterIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return Cluster
    
    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()
