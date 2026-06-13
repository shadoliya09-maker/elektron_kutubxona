from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, exceptions
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import *
from .models import UserConfirmation
from shared.utils import calculate_reading_time
from .serializers import *
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
import random

User = get_user_model()

@transaction.atomic
def create_borrowing(user, book_id, due_date):
    book = Book.objects.select_for_update().get(id=book_id)

    if book.available_copies <= 0:
        raise exceptions.ValidationError('kechirasiz ushbu kitob tugabdi')

    book.available_copies -=1
    book.save()

    borrowing = Borrowing.objects.create(
        user=user,
        book=book,
        due_date=due_date,
        status=Borrowing.Status.ACTIVE
    )
    return borrowing

@transaction.atomic
def return_book(borrowing_id):
    borrowing = Borrowing.objects.select_for_update().get(id=borrowing_id)

    if borrowing.status == Borrowing.Status.RETURNED:
        raise exceptions.ValidationError('bu kitob allaqachon qaytarib berilgan')

    book = borrowing.book
    book.available_copies += 1
    book.save()

    borrowing.return_date = timezone.now()
    borrowing.status = Borrowing.Status.RETURNED
    borrowing.save()

class BookViewSet(ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    permission_classes = [IsAuthenticated]

class PostDetailView(APIView):
    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            reading_time = calculate_reading_time(post.content)
            data = {
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at,
                'reading_time_minutes': reading_time
            }
            return Response(data, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post topilmadi'}, status=status.HTTP_404_NOT_FOUND)

class BorrowingViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == User.Roles.ADMIN:
            return Borrowing.objects.select_related(
                "user",
                "book"
            )

        return Borrowing.objects.select_related(
            "user",
            "book"
        ).filter(user=user)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer

        return BorrowingReadSerializer

class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            user = serializer.save()

            verification_code = str(
                random.randint(100000, 999999)
            )

            UserConfirmation.objects.create(
                user=user,
                code=verification_code
            )

        return Response(
            {
                "success": True,
                "message": "Ro'yxatdan o'tdingiz",
                "phone": user.phone,
            },
            status=status.HTTP_201_CREATED
        )

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class CommentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
            'success': True,
            'message': 'tabriklaymiz profilingiz yangilandi',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)

class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            user = User.objects.get(phone=phone)
            generated_code = str(random.randint(100000, 999999))

            with transaction.atomic():
                UserConfirmation.objects.filter(user=user, is_confirmed=False).delete()
                UserConfirmation.objects.create(
                    user=user,
                    code=generated_code
                )
                return Response({
                    'success': True,
                    'message': 'kod telingizga yuborildi',
                    'sms_code': generated_code
                }, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        user = get_object_or_404(
            User,
            phone=phone
        )

        confirmation = (
            UserConfirmation.objects.filter(
                user=user,
                code=code,
                is_confirmed=False
            ).last()
        )

        if not confirmation or confirmation.is_expired:
            return Response(
                {
                    "success": False,
                    "message": "Kod noto'g'ri yoki eskirgan"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            user.set_password(new_password)
            user.save()

            confirmation.is_confirmed = True
            confirmation.save()

        return Response(
            {
                "success": True,
                "message": "Parol muvaffaqiyatli o'zgartirildi"
            },
            status=status.HTTP_200_OK
        )

class ShaxsiyMalumotlarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        contect = {'message': 'tizimga kirishni uddaladingi'}
        return Response(contect)

class VerifyAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifySerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        confirmation = (
            UserConfirmation.objects.filter(
                user__phone=phone,
                code=code,
                is_confirmed=False
            ).last()
        )

        if not confirmation or confirmation.is_expired:
            return Response(
                {
                    "success": False,
                    "message": "Kod noto'g'ri yoki eskirgan"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            user = confirmation.user
            user.is_active = True
            user.save()

            confirmation.is_confirmed = True
            confirmation.save()

        return Response(
            {
                "success": True,
                "message": "Telefon raqam tasdiqlandi"
            },
            status=status.HTTP_200_OK
        )

class GetNewVerificationAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return Response({'phone': ['maydonni bosh qoldirmang']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'foydaalnnuvchi topilmadi'
            }, status=status.HTTP_404_NOT_FOUND)

        if user.is_active:
            return Response({
                'success': False,
                'message': 'foydalanuvchi llaqachon royxatdan otgan'
            }, status=status.HTTP_400_BAD_REQUEST)
        new_code = str(random.randint(100000, 999999))

        with transaction.atomic():
            UserConfirmation.objects.filter(user=user, is_confirmed=False).delete()
            UserConfirmation.objects.create(user=user, code=new_code)
            return Response({
                'success': True,
                'message': 'cod telefoningizga yuborildi',
            }, status=status.HTTP_200_OK)

class ChangeUserInformationView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        serializer = ChangeUserInformationSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'malumotlaringiz oozgsrtirildi',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')
        if not phone or not password:
            return Response({'message': 'telefon raqm va parol kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=phone, password=password)
        if user is not None:
            if not user.is_active:
                return Response({'message': 'profilingiz tasdiqlanmadi'}, status=status.HTTP_400_BAD_REQUEST)
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'phone': user.phone,
                    'full_name': user.full_name
                }
            }, status=status.HTTP_200_OK)
        return Response({'message': 'telefon raqm yoki paarolingiz xato terilgan'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'success': True, 'message': 'tizimdan chiqish qamalga oshirildi'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': 'notogri token yuboridi'}, status=status.HTTP_400_BAD_REQUEST)

class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like_queryset = PostLike.objects.filter(user=request.user, post=post)
        if like_queryset.exists():
            like_queryset.delete()
            return Response({"success": True, 'message': 'like olib tashlandi', 'liked': False}, status=status.HTTP_200_OK)
        else:
            PostLike.objects.create(user=request.user, post=post)
            return Response({"success": True, 'message': 'like qoshildi', 'liked': True}, status=status.HTTP_201_CREATED)

class CommentLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(
            Comment,
            id=comment_id
        )

        like_queryset = CommentLike.objects.filter(
            user=request.user,
            comment=comment
        )

        if like_queryset.exists():
            like_queryset.delete()

            return Response(
                {
                    "success": True,
                    "liked": False,
                    "message": "Like olib tashlandi"
                },
                status=status.HTTP_200_OK
            )

        CommentLike.objects.create(
            user=request.user,
            comment=comment
        )

        return Response(
            {
                "success": True,
                "liked": True,
                "message": "Like qo'shildi"
            },
            status=status.HTTP_201_CREATED
        )

class HomeView(APIView):
    def get(self, request):
        return Response({
            "message": "Elektron Kutubxona API ishlayapti"
        })