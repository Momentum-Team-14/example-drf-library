import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.constraints import UniqueConstraint
from django.core.validators import MaxValueValidator, MinValueValidator


class User(AbstractUser):
    pass


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publication_year = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(300),
            MaxValueValidator(datetime.date.today().year),
        ],
        null=True,
        blank=True,
    )
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    favorited_by = models.ManyToManyField(User, related_name="favorite_books")
    title_page = models.ImageField(upload_to="title_pages", null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["title", "author"], name="unique_by_author")
        ]

    def __repr__(self):
        return f"<Book title={self.title} pk={self.pk}>"

    def __str__(self):
        return f"{self.title} by {self.author}"

    def favorite_count(self):
        return self.favorited_by.count()


class BookRecord(models.Model):
    class ReadingState(models.TextChoices):
        WANT_TO_READ = "wr", "want to read"
        READING = "rg", "reading"
        READ = "rd", "read"

    book = models.ForeignKey(
        to="Book", on_delete=models.CASCADE, related_name="book_records"
    )
    reader = models.ForeignKey(
        to="User", on_delete=models.CASCADE, related_name="book_records"
    )
    reading_state = models.CharField(max_length=2, choices=ReadingState.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["book", "reader"], name="unique_book_record_for_user"
            )
        ]

    def __repr__(self):
        return f"<BookRecord pk={self.pk} reader_pk={self.reader.pk} book_pk={self.book.pk}>"

    def __str__(self):
        return f"{self.reader.username} {self.reading_state}: {self.book.title}"


class BookReview(models.Model):
    body = models.TextField()
    book = models.ForeignKey(
        to="Book", on_delete=models.CASCADE, related_name="reviews"
    )
    reviewed_by = models.ForeignKey(
        to="User", on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=["reviewed_by", "book"], name="unique_user_review")
        ]

    def __repr__(self):
        return (
            f"<BookReview pk={self.pk} book={self.book} reviewed_by={self.reviewed_by}>"
        )

    def __str__(self):
        return f"Review of {self.book.title}"
