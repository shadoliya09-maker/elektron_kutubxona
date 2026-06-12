from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

router = DefaultRouter()
router.register(r'xizmatlar', XizmatViewSet)
router.register(r'books', BookViewSet, basename='book')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'borrowings', BorrowingViewSet, basename='borrowing')

urlpatterns = [
    path('', HomeView.as_view()),
    path('', include(router.urls)),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('verify/', VerifyAPIView.as_view(), name='verify'),
    path('resend_code/', GetNewVerificationAPIView.as_view(), name='resend_code'),
    path('change_user_info/', ChangeUserInformationView.as_view(), name='change_user_info'),
    path('comments/', CommentCreateView.as_view(), name='comments_created'),
    path('posts/<int:post_id>/like/', PostLikeView.as_view(), name='post-like'),
    path('comments/<int:comment_id>/like/', CommentLikeView.as_view(), name='comment-like'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
 ]