from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from shared.models import BaseModel

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        LIBRARIAN = "librarian", "Kutubxonachi"
        STUDENT = "student", "Talaba"

    username = None

    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="books")
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    total_copies = models.PositiveIntegerField()
    available_copies = models.PositiveIntegerField()

    def clean(self):
        if self.available_copies > self.total_copies:
            raise ValidationError(
                "available_copies total_copies dan katta bo'lishi mumkin emas"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Borrowing(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        RETURNED = "returned", "Qaytarilgan"
        OVERDUE = "overdue", "Muddati o'tgan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    def __str__(self):
        return f"{self.user.full_name} - {self.book.title}"


class Post(BaseModel):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author_name = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class UserConfirmation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="confirmations")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return timezone.now() > (
            self.created_at + timedelta(minutes=5)
        )

    def __str__(self):
        return f"{self.user.phone} - {self.code}"


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()

    def __str__(self):
        return f"{self.user.full_name} - {self.post.title}"


class PostLike(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_post_like")
        ]

    def __str__(self):
        return f"{self.user.full_name} -> {self.post.title}"


class CommentLike(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "comment"], name="unique_comment_like")
        ]

    def __str__(self):
        return f"{self.user.full_name} -> Comment #{self.comment.id}"
