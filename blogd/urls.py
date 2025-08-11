from django.urls import path, include
from .views import (
    UserRegisterView, UserLoginView, UserLogoutView, CurrentUserView,
    BlogCategoryListView, BlogCategoryDetailView,
    BlogPostListView, BlogPostDetailView, LatestBlogPostsView, AdminBlogPostsView,
    CommentListView, CommentDetailView, ApproveCommentView,
    LikeCreateView, LikeDeleteView,
    DashboardView
)

urlpatterns = [
    # Authentication URLs
    path('auth/register/', UserRegisterView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/logout/', UserLogoutView.as_view(), name='logout'),
    path('auth/user/', CurrentUserView.as_view(), name='current-user'),
    
    # Blog Category URLs
    path('categories/', BlogCategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', BlogCategoryDetailView.as_view(), name='category-detail'),
    
    # Blog Post URLs
    path('posts/', BlogPostListView.as_view(), name='post-list'),
    path('posts/<int:pk>/', BlogPostDetailView.as_view(), name='post-detail'),
    path('posts/latest/', LatestBlogPostsView.as_view(), name='latest-posts'),
    path('posts/admin/', AdminBlogPostsView.as_view(), name='admin-posts'),
    
    # Comment URLs
    path('posts/<int:post_id>/comments/', CommentListView.as_view(), name='comment-list'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<int:pk>/approve/', ApproveCommentView.as_view(), name='approve-comment'),
    
    # Like URLs
    path('posts/<int:post_id>/like/', LikeCreateView.as_view(), name='like-create'),
    path('posts/<int:post_id>/unlike/', LikeDeleteView.as_view(), name='like-delete'),
    
    # Dashboard URL
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]