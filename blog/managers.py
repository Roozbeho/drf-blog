from django.contrib.postgres.search import (SearchQuery, SearchRank,
                                            SearchVector)
from django.db.models import Manager, Q, QuerySet

class PostQuerySet(QuerySet):
    def search_filter(self, query_search):
        search_vector = (
            SearchVector("title", weight="A")
            + SearchVector("body", weight="B")
            + SearchVector("tag__name", weight="C")
        )
        search_query = SearchQuery(query_search, search_type="phrase")
        return self.annotate(rank=SearchRank(search_vector, search_query)).order_by("-rank")

    def order_post(self, filter, asc):
        filter_methods = {
            "most_viewed": self._order_posts_by_view,
            "created_time": self._order_posts_by_created_time,
        }
        order_method = filter_methods.get(filter, self._order_posts_by_created_time)
        return order_method(asc)

    def _order_posts_by_view(self, asc):
        if asc:
            return self.order_by("visit_counter")
        return self.order_by("-visit_counter")

    def _order_posts_by_created_time(self, asc):
        if asc:
            return self.order_by("created_at")
        return self.all()


class PostCustomManager(Manager):
    def get_queryset(self):
        return PostQuerySet(self.model, using=self._db).filter(status=self.model.Status.PUBLISHED)
    
    def get_queryset_unfiltered(self):
        return PostQuerySet(self.model, using=self._db)

    def get_premium_posts(self, premium=False):
        qs = self.get_queryset()
        return qs if premium else qs.filter(premium=False)

    def search_post(self, query_search: str):
        return self.get_premium_posts().search_filter(query_search)

    def order_post(self, filter="most_viewed", asc=True):
        if filter not in ["most_viewed", "created_time"]:
            raise ValueError(f"Invalid filter: {filter}")
        return self.get_premium_posts().order_post(filter, asc)

    def most_related_posts(self, post):
        return self.get_queryset().filter(tag__in=post.tag.all()).exclude(id=post.id).distinct()