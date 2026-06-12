from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
import re
from .models import *

class XizmatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Xizmat
        fields = '__all__'

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class BookSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "category",
            "category_name",
            "title",
            "author",
            "total_copies",
            "available_copies",
        ]
        read_only_fields = ["available_copies"]

    def create(self, validated_data):
        validated_data["available_copies"] = validated_data["total_copies"]
        return super().create(validated_data)


class BorrowingReadSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    user_name = serializers.CharField(
        source="user.full_name",
        read_only=True
    )

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "user",
            "user_name",
            "book",
            "borrow_date",
            "due_date",
            "return_date",
            "status",
        ]


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["book", "due_date"]

    def validate_due_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Qaytarish sanasi hozirgi vaqtdan keyin bo'lishi kerak."
            )
        return value

    def validate(self, attrs):
        book = attrs["book"]

        with transaction.atomic():
            locked_book = (
                Book.objects
                .select_for_update()
                .get(id=book.id)
            )

            if locked_book.available_copies <= 0:
                raise serializers.ValidationError(
                    {"book": "Kitob mavjud emas."}
                )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        book = validated_data["book"]

        with transaction.atomic():
            locked_book = (
                Book.objects
                .select_for_update()
                .get(id=book.id)
            )

            if locked_book.available_copies <= 0:
                raise serializers.ValidationError(
                    {"book": "Kitob mavjud emas."}
                )

            locked_book.available_copies -= 1
            locked_book.save()

            borrowing = Borrowing.objects.create(
                user=user,
                book=locked_book,
                due_date=validated_data["due_date"],
                status=Borrowing.Status.ACTIVE
            )

        return borrowing


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "full_name",
            "role",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "phone",
            "role",
            "date_joined",
        ]


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source="user.full_name",
        read_only=True
    )

    user_phone = serializers.CharField(
        source="user.phone",
        read_only=True
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "user_name",
            "user_phone",
            "text",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class ForgetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)

    def validate_phone(self, value):
        if not User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Bu telefon raqamli foydalanuvchi topilmadi."
            )
        return value


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)

    code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6
    )

    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=6
    )

    def validate_new_password(self, value):
        if value.isdigit():
            raise serializers.ValidationError(
                "Parol faqat raqamlardan iborat bo'lishi mumkin emas."
            )
        return value


class VerifySerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    code = serializers.CharField(required=True)


class ChangeUserInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "full_name",
            "phone",
        ]

    def validate_phone(self, value):
        phone_regex = r'^\+998\d{9}$'

        if not re.match(phone_regex, value):
            raise serializers.ValidationError(
                "Telefon raqam noto'g'ri formatda."
            )

        current_user = self.instance

        if (
            User.objects
            .filter(phone=value)
            .exclude(id=current_user.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "Bu telefon raqam band."
            )

        return value


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        required=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "full_name",
            "password",
        ]

    def validate_phone(self, value):
        phone_regex = r'^\+998\d{9}$'

        if not re.match(phone_regex, value):
            raise serializers.ValidationError(
                "Telefon raqam noto'g'ri formatda."
            )

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Bu telefon raqam allaqachon mavjud."
            )

        return value

    def validate_password(self, value):
        if value.isdigit():
            raise serializers.ValidationError(
                "Parol faqat raqamlardan iborat bo'lishi mumkin emas."
            )

        return value

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            is_active=False,
            **validated_data
        )

        return user
