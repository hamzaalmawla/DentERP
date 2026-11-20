"""List pagination for every API list (design section 7): ``?page=`` and ``?page_size=``,
20 rows by default and at most 100."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
