from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
DEFAULT_PAGE = 25
class PostListPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_size = 25

    def get_paginated_response(self, data):
        return Response({
            'links':{
                'next': self.get_next_link(),
                'prev': self.get_previous_link()
            },
            'total': self.page.paginator.count,
            'result': data
        })
    
class CommentListPagination(PageNumberPagination):
    page_size_query_param = 'cmnt_size'
    max_page_size = 20
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'prev': self.get_previous_link()
            },
            'total': self.page.paginator.count,
            'comments': data
        })