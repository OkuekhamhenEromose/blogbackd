from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError  # Add this import
from django.contrib.auth.models import User
from .models import BlogPost, BlogCategory, Comment, Like, UserProfile
from .serializers import (
    BlogPostSerializer, BlogCategorySerializer, CommentSerializer, 
    LikeSerializer, UserRegisterSerializer, UserSerializer, UserProfileSerializer
)
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

# Authentication Views
class UserRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user': UserSerializer(user).data,
                'token': serializer.get_token(user),
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Both username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Get user profile
        profile = UserProfile.objects.get(user=user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'is_blog_admin': profile.is_blog_admin,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        logout(request)
        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        return Response({
            'user': UserSerializer(request.user).data,
            'is_blog_admin': profile.is_blog_admin
        }, status=status.HTTP_200_OK)

# Blog Category Views
class BlogCategoryListView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permission() for permission in [IsAuthenticated, permissions.IsAdminUser]]
        return super().get_permissions()

class BlogCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permission() for permission in [IsAuthenticated, permissions.IsAdminUser]]
        return super().get_permissions()

# Blog Post Views
class BlogPostListView(generics.ListCreateAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = BlogPost.objects.filter(published=True).order_by('-published_date')
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category__id=category_id)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) |
                Q(author__username__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        # Only allow blog admins to create posts
        profile = UserProfile.objects.get(user=self.request.user)
        if not profile.is_blog_admin:
            raise permissions.PermissionDenied("Only blog admins can create posts")
        serializer.save(author=self.request.user)

class BlogPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # Only allow the author or admin to edit/delete
            obj = self.get_object()
            profile = UserProfile.objects.get(user=self.request.user)
            if obj.author != self.request.user and not profile.is_blog_admin:
                raise permissions.PermissionDenied("You don't have permission to perform this action")
        return super().get_permissions()

class LatestBlogPostsView(generics.ListAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Get posts from the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return BlogPost.objects.filter(
            published=True, 
            published_date__gte=thirty_days_ago
        ).order_by('-published_date')[:5]

class AdminBlogPostsView(generics.ListAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Check if user is a blog admin
        profile = UserProfile.objects.get(user=self.request.user)
        if not profile.is_blog_admin:
            raise permissions.PermissionDenied("Only blog admins can access this view")
        
        # Return all posts (including unpublished) for the admin
        return BlogPost.objects.filter(author=self.request.user).order_by('-created_at')

# Comment Views
class CommentListView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        post_id = self.kwargs.get('post_id')
        return Comment.objects.filter(post__id=post_id, approved=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        post = get_object_or_404(BlogPost, pk=self.kwargs.get('post_id'))
        serializer.save(author=self.request.user, post=post)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        obj = self.get_object()
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # Only allow the author or admin to edit/delete
            profile = UserProfile.objects.get(user=self.request.user)
            if obj.author != self.request.user and not profile.is_blog_admin:
                raise permissions.PermissionDenied("You don't have permission to perform this action")
        return super().get_permissions()

class ApproveCommentView(generics.UpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, *args, **kwargs):
        # Only allow blog admins to approve comments
        profile = UserProfile.objects.get(user=self.request.user)
        if not profile.is_blog_admin:
            raise permissions.PermissionDenied("Only blog admins can approve comments")
        
        comment = self.get_object()
        comment.approved = True
        comment.save()
        return Response({'status': 'comment approved'})

# Like Views
class LikeCreateView(generics.CreateAPIView):
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        post = get_object_or_404(BlogPost, pk=self.kwargs.get('post_id'))
        # Check if user already liked this post
        if Like.objects.filter(post=post, user=self.request.user).exists():
            raise ValidationError("You already liked this post")
        serializer.save(user=self.request.user, post=post)

class LikeDeleteView(generics.DestroyAPIView):
    queryset = Like.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        post = get_object_or_404(BlogPost, pk=self.kwargs.get('post_id'))
        return get_object_or_404(Like, post=post, user=self.request.user)

# Dashboard Views
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        
        if profile.is_blog_admin:
            # Admin dashboard data
            total_posts = BlogPost.objects.filter(author=request.user).count()
            published_posts = BlogPost.objects.filter(author=request.user, published=True).count()
            total_comments = Comment.objects.filter(post__author=request.user).count()
            pending_comments = Comment.objects.filter(post__author=request.user, approved=False).count()
            
            return Response({
                'is_admin': True,
                'total_posts': total_posts,
                'published_posts': published_posts,
                'total_comments': total_comments,
                'pending_comments': pending_comments
            })
        else:
            # User dashboard data
            liked_posts = Like.objects.filter(user=request.user).count()
            comments_made = Comment.objects.filter(author=request.user).count()
            
            return Response({
                'is_admin': False,
                'liked_posts': liked_posts,
                'comments_made': comments_made
            })