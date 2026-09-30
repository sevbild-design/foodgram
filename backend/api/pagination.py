from api.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from rest_framework.pagination import PageNumberPagination


class LimitPageNumberPagination(PageNumberPagination):
    """
    Пагинация с возможностью задавать размер страницы.

    limit - параметр, задающий размер страницы.
    Если не передан limit, вернется значение по умолчанию,
    заданное в константе DEFAULT_PAGE_SIZE.
    Максимальный размер страницы задан константой MAX_PAGE_SIZE.
    """

    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE
