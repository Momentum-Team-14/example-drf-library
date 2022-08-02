from django.db import IntegrityError
from django.views.defaults import bad_request
from psycopg2.errors import UniqueViolation
from rest_framework import status
from rest_framework.parsers import JSONParser, FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    get_object_or_404,
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Book, BookRecord, BookReview
from .serializers import (
    BookSerializer,
    BookDetailSerializer,
    BookRecordSerializer,
    BookReviewSerializer,
    FavoriteSerializer,
)
from .custom_permissions import (
    IsAdminOrReadOnly,
    IsReaderOrReadOnly,
)
from api import serializers
from django.db.models import Count


class BookViewSet(ModelViewSet):
    serializer_class = BookDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action in ["list"]:
            return BookSerializer
        return super().get_serializer_class()

    def get_parsers(self):
        if self.request.FILES:
            self.parser_classes.append(FileUploadParser)
        return [parser() for parser in self.parser_classes]

    @action(detail=False)
    def featured(self, request):
        featured_books = Book.objects.filter(featured=True)
        serializer = self.get_serializer(featured_books, many=True)
        return Response(serializer.data)

    @action(detail=False)
    def favorites(self, request):
        favorited_books = request.user.favorite_books.all()
        serializer = self.get_serializer(favorited_books, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            error_data = {
                "error": "Unique constraint violation: there is already a book with this title by this author."
            }
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        # we want this to work for requests that don't include a search term as well
        queryset = Book.objects.all().order_by("title")
        # handle the case where we have query params that include a "search" key
        # if there are no search terms that match "search" this will be None
        search_term = self.request.query_params.get("search")
        if search_term is not None:
            # filter using the search term
            queryset = Book.objects.filter(title__icontains=search_term).order_by(
                "title"
            )

        return queryset


class BookRecordViewSet(ModelViewSet):
    queryset = BookRecord.objects.all()
    serializer_class = BookRecordSerializer
    permission_classes = [IsAuthenticated, IsReaderOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(reader=self.request.user, book=self.kwargs["book_pk"])

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as error:
            error_data = {
                "error": "Unique constraint violation: this user has already created a book record for this book."
            }
            return Response(error_data, status=400)

    def perform_create(self, serializer):
        book = get_object_or_404(Book, pk=self.kwargs["book_pk"])
        serializer.save(reader=self.request.user, book=book)


class BookReviewListCreateView(ListCreateAPIView):
    serializer_class = BookReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = BookReview.objects.filter(book_id=self.kwargs["book_pk"])

        return queryset

    def perform_create(self, serializer, **kwargs):
        book = get_object_or_404(Book, pk=self.kwargs["book_pk"])
        serializer.save(reviewed_by=self.request.user, book=book)


class BookReviewDetailView(RetrieveDestroyAPIView):
    serializer_class = BookReviewSerializer
    queryset = BookReview.objects.all()


class CreateFavoriteView(APIView):
    """
    Create related objects in a M2M relationship.
    See the favorited_by field on the Book model.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, **kwargs):
        # I need to know the user
        user = self.request.user
        # I need to know the book
        book = get_object_or_404(Book, pk=self.kwargs["book_pk"])
        # I need to add the book to the user's favorites
        # This uses the related name for the relation from the user model
        user.favorite_books.add(book)
        # use a serializer to serialize data about the book we just favorited
        serializer = BookDetailSerializer(book, context={"request": request})
        # return a response
        return Response(serializer.data, status=201)


class BookReviewSearchView(ListAPIView):
    serializer_class = BookReviewSerializer
    search_term = ""

    def get_queryset(self):
        search_term = self.request.query_params.get("search") or self.search_term
        # this is using the search method for postgres full-text search
        # https://docs.djangoproject.com/en/4.0/ref/contrib/postgres/search/#the-search-lookup
        return BookReview.objects.filter(body__search=search_term)
