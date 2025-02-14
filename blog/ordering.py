from rest_framework import filters


class CustomOrderingFilter(filters.OrderingFilter):
    """A custom ordering filter for blog posts.

    This class extends the OrderingFilter to provide custom ordering functionality
    for blog posts based on view count and creation time.
    """

    def get_valid_fields(self, queryset, view, context={}):
        """
        Define the valid fields for ordering.

        Returns:
            list: A list of tuples containing valid ordering fields.
        """
        return [("view", "view"), ("created", "created")]

    def filter_queryset(self, request, queryset, view):
        """
        Apply custom filtering and ordering to the queryset.

        This method filters the queryset based on tags (if provided) and applies
        custom ordering based on the 'ordering' query parameter.

        Returns:
            QuerySet: The filtered and ordered queryset.
        """
        query_params = request.query_params

        if query_params.get("tag"):
            queryset = queryset.filter(tag__slug=query_params.get("tag"))

        ordering_filter_mapping = {
            "view": ("most_viewed", True),
            "-view": ("most_viewed", False),
            "created": ("created_time", True),
            "-created": ("created_time", False),
        }

        if query_params.get("ordering") in ordering_filter_mapping.keys():
            queryset = queryset.order_post(*ordering_filter_mapping[query_params.get("ordering")])
        return queryset
    