from rest_framework.pagination import PageNumberPagination


class LimitPageNumberPagination(PageNumberPagination):
    """Пагинация с возможностью задавать размер страницы."""

    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100