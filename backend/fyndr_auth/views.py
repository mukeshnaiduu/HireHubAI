
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from .models import User, JobSeekerProfile, RecruiterProfile, CompanyProfile, CompanyRecruiterRelationship
from .serializers import (
    RegisterSerializer, LoginSerializer, 
    JobSeekerProfileSerializer, RecruiterProfileSerializer, CompanyProfileSerializer,
    JobSeekerOnboardingSerializer
)

# Profile view for authenticated user
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
        }
        profile = None
        profile_complete = False
        
        if user.role == 'job_seeker':
            try:
                profile_obj = JobSeekerProfile.objects.get(user=user)
                profile = JobSeekerProfileSerializer(profile_obj).data
                profile_complete = profile_obj.is_complete
                # Update user data with profile info
                if profile_obj.first_name:
                    user_data['first_name'] = profile_obj.first_name
                if profile_obj.last_name:
                    user_data['last_name'] = profile_obj.last_name
                if profile_obj.email:
                    user_data['email'] = profile_obj.email
                # Create a display name for profile dropdown
                user_data['name'] = profile_obj.full_name or f"{user_data['first_name']} {user_data['last_name']}"
            except JobSeekerProfile.DoesNotExist:
                profile = None
                user_data['name'] = f"{user_data['first_name']} {user_data['last_name']}"
                
        elif user.role == 'recruiter':
            try:
                profile_obj = RecruiterProfile.objects.get(user=user)
                profile = RecruiterProfileSerializer(profile_obj).data
                profile_complete = profile_obj.is_complete
                # Update user data with profile info
                if profile_obj.first_name:
                    user_data['first_name'] = profile_obj.first_name
                if profile_obj.last_name:
                    user_data['last_name'] = profile_obj.last_name
                if profile_obj.email:
                    user_data['email'] = profile_obj.email
                user_data['name'] = profile_obj.full_name or f"{user_data['first_name']} {user_data['last_name']}"
            except RecruiterProfile.DoesNotExist:
                profile = None
                user_data['name'] = f"{user_data['first_name']} {user_data['last_name']}"
                
        elif user.role == 'company':
            try:
                profile_obj = CompanyProfile.objects.get(user=user)
                profile = CompanyProfileSerializer(profile_obj).data
                profile_complete = profile_obj.is_complete
                user_data['name'] = profile_obj.company_name or f"{user_data['first_name']} {user_data['last_name']}"
            except CompanyProfile.DoesNotExist:
                profile = None
                user_data['name'] = f"{user_data['first_name']} {user_data['last_name']}"
        else:
            profile_complete = True  # Admins always considered complete
            user_data['name'] = f"{user_data['first_name']} {user_data['last_name']}"
            
        user_data['profile'] = profile
        user_data['profile_complete'] = profile_complete
        # Backward compatibility
        user_data['onboarding'] = profile
        user_data['onboarding_complete'] = profile_complete
        
        return Response(user_data)

    def put(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()
        
        # Update user fields
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.save()
        
        # Update or create profile based on user role
        if user.role == 'job_seeker' and 'profile' in data:
            profile_data = data['profile']
            try:
                profile = JobSeekerProfile.objects.get(user=user)
                serializer = JobSeekerProfileSerializer(profile, data=profile_data, partial=True)
            except JobSeekerProfile.DoesNotExist:
                profile_data['user'] = user.id
                serializer = JobSeekerProfileSerializer(data=profile_data)
            
            if serializer.is_valid():
                serializer.save(user=user)
            else:
                raise ValidationError(serializer.errors)
                
        elif user.role == 'recruiter' and 'profile' in data:
            profile_data = data['profile']
            try:
                profile = RecruiterProfile.objects.get(user=user)
                serializer = RecruiterProfileSerializer(profile, data=profile_data, partial=True)
            except RecruiterProfile.DoesNotExist:
                profile_data['user'] = user.id
                serializer = RecruiterProfileSerializer(data=profile_data)
            
            if serializer.is_valid():
                serializer.save(user=user)
            else:
                raise ValidationError(serializer.errors)
                
        elif user.role == 'company' and 'profile' in data:
            profile_data = data['profile']
            try:
                profile = CompanyProfile.objects.get(user=user)
                serializer = CompanyProfileSerializer(profile, data=profile_data, partial=True)
            except CompanyProfile.DoesNotExist:
                profile_data['user'] = user.id
                serializer = CompanyProfileSerializer(data=profile_data)
            
            if serializer.is_valid():
                serializer.save(user=user)
            else:
                raise ValidationError(serializer.errors)
        
        return self.get(request, *args, **kwargs)
from rest_framework import generics, status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
import base64


class FileServeView(APIView):
    """Serve files stored in database as binary data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, model_type, profile_id, file_type):
        try:
            if model_type == 'jobseeker':
                profile = JobSeekerProfile.objects.get(id=profile_id, user=request.user)
                
                if file_type == 'profile_image':
                    file_data = profile.profile_image_data
                    filename = profile.profile_image_filename
                    content_type = profile.profile_image_content_type
                elif file_type == 'resume':
                    file_data = profile.resume_data
                    filename = profile.resume_filename
                    content_type = profile.resume_content_type
                elif file_type == 'cover_letter':
                    file_data = profile.cover_letter_data
                    filename = profile.cover_letter_filename
                    content_type = profile.cover_letter_content_type
                elif file_type == 'portfolio':
                    file_data = profile.portfolio_pdf_data
                    filename = profile.portfolio_pdf_filename
                    content_type = profile.portfolio_pdf_content_type
                else:
                    return Response({'error': 'Invalid file type'}, status=404)
                    
            elif model_type == 'recruiter':
                profile = RecruiterProfile.objects.get(id=profile_id, user=request.user)
                
                if file_type == 'profile_image':
                    file_data = profile.profile_image_data
                    filename = profile.profile_image_filename
                    content_type = profile.profile_image_content_type
                elif file_type == 'resume':
                    file_data = profile.resume_data
                    filename = profile.resume_filename
                    content_type = profile.resume_content_type
                else:
                    return Response({'error': 'Invalid file type'}, status=404)
                    
            elif model_type == 'company':
                profile = CompanyProfile.objects.get(id=profile_id, user=request.user)
                
                if file_type == 'logo':
                    file_data = profile.logo_data
                    filename = profile.logo_filename
                    content_type = profile.logo_content_type
                elif file_type == 'brochure':
                    file_data = profile.company_brochure_data
                    filename = profile.company_brochure_filename
                    content_type = profile.company_brochure_content_type
                else:
                    return Response({'error': 'Invalid file type'}, status=404)
            else:
                return Response({'error': 'Invalid model type'}, status=404)
                
            if not file_data:
                return Response({'error': 'File not found'}, status=404)
                
            response = HttpResponse(file_data, content_type=content_type or 'application/octet-stream')
            if filename:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
            
        except (JobSeekerProfile.DoesNotExist, RecruiterProfile.DoesNotExist, CompanyProfile.DoesNotExist):
            return Response({'error': 'Profile not found'}, status=404)
        except Exception as e:
            return Response({'error': f'Error serving file: {str(e)}'}, status=500)


class FileUploadView(APIView):
    """Handle file uploads for profiles"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        print(f"=== FILE UPLOAD DEBUG ===")
        print(f"User authenticated: {request.user.is_authenticated}")
        print(f"User: {request.user}")
        print(f"User type: {type(request.user)}")
        print(f"Auth header: {request.META.get('HTTP_AUTHORIZATION', 'None')}")
        
        # Check if user is AnonymousUser
        from django.contrib.auth.models import AnonymousUser
        if isinstance(request.user, AnonymousUser):
            print("User is AnonymousUser - JWT authentication failed")
            return Response({'error': 'Authentication required', 'detail': 'JWT token invalid or expired'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not request.user.is_authenticated:
            print("User not authenticated")
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if 'file' not in request.FILES:
            print("No file in request.FILES")
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        file_type = request.POST.get('type', 'resume')  # resume, cover_letter, portfolio, logo, brochure
        
        print(f"Uploaded file: {uploaded_file.name}")
        print(f"File size: {uploaded_file.size}")
        print(f"File type: {file_type}")
        print(f"Content type: {uploaded_file.content_type}")
        
        # Validate file size (10MB limit)
        if uploaded_file.size > 10 * 1024 * 1024:
            return Response({'error': 'File size exceeds 10MB limit'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type based on upload type
        allowed_extensions = {
            'resume': ['.pdf', '.doc', '.docx'],
            'cover_letter': ['.pdf', '.doc', '.docx'],
            'portfolio': ['.pdf'],
            'profile_image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'logo': ['.jpg', '.jpeg', '.png', '.gif'],
            'brochure': ['.pdf']
        }
        
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        print(f"File extension detected: '{file_extension}'")
        print(f"Allowed extensions for {file_type}: {allowed_extensions.get(file_type, [])}")
        
        if file_extension not in allowed_extensions.get(file_type, []):
            return Response({
                'error': f'Invalid file type. Allowed types for {file_type}: {", ".join(allowed_extensions.get(file_type, []))}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Read file data
            file_data = uploaded_file.read()
            
            # Get or create the user's profile
            if request.user.role == 'job_seeker':
                profile, created = JobSeekerProfile.objects.get_or_create(user=request.user)
                
                # Save file data to appropriate field
                if file_type == 'resume':
                    profile.resume_data = file_data
                    profile.resume_filename = uploaded_file.name
                    profile.resume_content_type = uploaded_file.content_type
                    profile.resume_size = uploaded_file.size
                elif file_type == 'cover_letter':
                    profile.cover_letter_data = file_data
                    profile.cover_letter_filename = uploaded_file.name
                    profile.cover_letter_content_type = uploaded_file.content_type
                    profile.cover_letter_size = uploaded_file.size
                elif file_type == 'portfolio':
                    profile.portfolio_pdf_data = file_data
                    profile.portfolio_pdf_filename = uploaded_file.name
                    profile.portfolio_pdf_content_type = uploaded_file.content_type
                    profile.portfolio_pdf_size = uploaded_file.size
                elif file_type == 'profile_image':
                    profile.profile_image_data = file_data
                    profile.profile_image_filename = uploaded_file.name
                    profile.profile_image_content_type = uploaded_file.content_type
                    profile.profile_image_size = uploaded_file.size
                
                profile.save()
                
                # Generate file URL for serving from database
                if file_type == 'resume' and profile.resume_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/resume/')
                elif file_type == 'cover_letter' and profile.cover_letter_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/cover_letter/')
                elif file_type == 'portfolio' and profile.portfolio_pdf_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/portfolio/')
                elif file_type == 'profile_image' and profile.profile_image_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/profile_image/')
                else:
                    file_url = None
                    
            elif request.user.role == 'recruiter':
                profile, created = RecruiterProfile.objects.get_or_create(user=request.user)
                
                if file_type == 'profile_image':
                    profile.profile_image_data = file_data
                    profile.profile_image_filename = uploaded_file.name
                    profile.profile_image_content_type = uploaded_file.content_type
                    profile.profile_image_size = uploaded_file.size
                elif file_type == 'resume':
                    profile.resume_data = file_data
                    profile.resume_filename = uploaded_file.name
                    profile.resume_content_type = uploaded_file.content_type
                    profile.resume_size = uploaded_file.size
                
                profile.save()
                
                # Generate file URL for serving from database
                if file_type == 'profile_image' and profile.profile_image_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/recruiter/{profile.id}/profile_image/')
                elif file_type == 'resume' and profile.resume_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/recruiter/{profile.id}/resume/')
                else:
                    file_url = None
                    
            elif request.user.role == 'company':
                profile, created = CompanyProfile.objects.get_or_create(user=request.user)
                
                if file_type == 'logo':
                    profile.logo_data = file_data
                    profile.logo_filename = uploaded_file.name
                    profile.logo_content_type = uploaded_file.content_type
                    profile.logo_size = uploaded_file.size
                elif file_type == 'brochure':
                    profile.company_brochure_data = file_data
                    profile.company_brochure_filename = uploaded_file.name
                    profile.company_brochure_content_type = uploaded_file.content_type
                    profile.company_brochure_size = uploaded_file.size
                
                profile.save()
                
                # Generate file URL for serving from database
                if file_type == 'logo' and profile.logo_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/company/{profile.id}/logo/')
                elif file_type == 'brochure' and profile.company_brochure_data:
                    file_url = request.build_absolute_uri(f'/api/auth/files/company/{profile.id}/brochure/')
                else:
                    file_url = None
            else:
                return Response({'error': 'Invalid user role'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'filename': uploaded_file.name,
                'size': uploaded_file.size,
                'url': file_url,
                'type': uploaded_file.content_type,
                'uploaded_at': profile.updated_at.isoformat() if hasattr(profile, 'updated_at') else None
            })
            
        except Exception as e:
            return Response({'error': f'Upload failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Issue JWT tokens upon successful registration
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': user.role,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Email not registered
            raise ValidationError({'email': ['No account found with this email.']})
        user = authenticate(username=user.username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'role': user.role,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
        # Incorrect password
        raise ValidationError({'password': ['Incorrect password.']})


class JobSeekerProfileView(generics.RetrieveUpdateAPIView):
    """Main view for Job Seeker Profile operations"""
    serializer_class = JobSeekerProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = JobSeekerProfile.objects.all()

    def get_object(self):
        profile, created = JobSeekerProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            # Try to get existing profile data
            profile = JobSeekerProfile.objects.get(user=user)
            serializer = self.get_serializer(profile)
            data = serializer.data
            
            # Add file URLs to the response
            if profile.resume_data:
                data['resume'] = {
                    'name': profile.resume_filename or 'resume',
                    'url': request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/resume/'),
                    'size': profile.resume_size or 0,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            
            if profile.profile_image_data:
                data['profile_image'] = {
                    'name': profile.profile_image_filename or 'profile_image',
                    'url': request.build_absolute_uri(f'/api/auth/files/jobseeker/{profile.id}/profile_image/'),
                    'size': profile.profile_image_size or 0,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            elif profile.profile_image_url:
                data['profile_image'] = {
                    'url': profile.profile_image_url,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            
            return Response(data)
        except JobSeekerProfile.DoesNotExist:
            # Pre-populate with user data from User table
            initial_data = {
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'email': user.email or '',
            }
            return Response(initial_data)

    def post(self, request, *args, **kwargs):
        print(f"=== JOBSEEKER ONBOARDING DEBUG ===")
        print(f"Request data: {request.data}")
        print(f"Request FILES: {request.FILES}")
        print(f"User: {request.user}")
        
        user = request.user
        data = request.data.copy()
        
        # Pre-populate with user data if not provided
        if not data.get('first_name') and user.first_name:
            data['first_name'] = user.first_name
        if not data.get('last_name') and user.last_name:
            data['last_name'] = user.last_name
        if not data.get('email') and user.email:
            data['email'] = user.email
            
        # Handle empty string date fields - convert to None for Django DateField
        date_fields = ['availability_date']
        for field in date_fields:
            if field in data and data[field] == '':
                data[field] = None
                print(f"Converted empty string to None for date field: {field}")
        
        # Handle empty string decimal fields - convert to None for Django DecimalField
        decimal_fields = ['salary_min', 'salary_max']
        for field in decimal_fields:
            if field in data and data[field] == '':
                data[field] = None
                print(f"Converted empty string to None for decimal field: {field}")
        
        # Handle profile_image field - if it's a URL from file upload, store it in profile_image_url
        if 'profile_image' in data and data['profile_image']:
            if data['profile_image'].startswith('http'):
                # This is an uploaded file URL, store in profile_image_url field
                data['profile_image_url'] = data['profile_image']
                print(f"Set profile_image_url to: {data['profile_image_url']}")
            elif data['profile_image'].startswith('blob:'):
                # This is a blob URL, ignore it since the actual file should be uploaded separately
                print(f"Ignoring blob URL: {data['profile_image']}")
            # Remove the profile_image field since it's not a model field
            del data['profile_image']
            
        print(f"Processed data: {data}")
            
        # Only one profile per user: update if exists, else create
        try:
            profile = JobSeekerProfile.objects.get(user=user)
            serializer = self.get_serializer(profile, data=data, partial=True)
            print(f"Updating existing profile: {profile.id}")
        except JobSeekerProfile.DoesNotExist:
            serializer = self.get_serializer(data=data)
            print("Creating new profile")
        
        print(f"Serializer is valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            
        serializer.is_valid(raise_exception=True)
        profile_obj = serializer.save(user=user)
        
        # Mark profile as complete when successfully saved with minimum required fields
        if profile_obj.first_name and profile_obj.email and profile_obj.phone:
            profile_obj.is_complete = True
            profile_obj.save(update_fields=['is_complete'])
            print(f"Profile marked as complete: {profile_obj.is_complete}")
        
        # Update User model with profile data
        if profile_obj.first_name and profile_obj.first_name != user.first_name:
            user.first_name = profile_obj.first_name
        if profile_obj.last_name and profile_obj.last_name != user.last_name:
            user.last_name = profile_obj.last_name
        if profile_obj.email and profile_obj.email != user.email:
            user.email = profile_obj.email
        user.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecruiterProfileView(generics.RetrieveUpdateAPIView):
    """Main view for Recruiter Profile operations"""
    serializer_class = RecruiterProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = RecruiterProfile.objects.all()

    def get_object(self):
        profile, created = RecruiterProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            profile = RecruiterProfile.objects.get(user=user)
            serializer = self.get_serializer(profile)
            data = serializer.data
            
            # Add file URLs to the response
            if profile.profile_image_data:
                data['profile_image'] = {
                    'name': profile.profile_image_filename or 'profile_image',
                    'url': request.build_absolute_uri(f'/api/auth/files/recruiter/{profile.id}/profile_image/'),
                    'size': profile.profile_image_size or 0,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            elif profile.profile_image_url:
                data['profile_image'] = {
                    'url': profile.profile_image_url,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            
            if profile.resume_data:
                data['resume'] = {
                    'name': profile.resume_filename or 'resume',
                    'url': request.build_absolute_uri(f'/api/auth/files/recruiter/{profile.id}/resume/'),
                    'size': profile.resume_size or 0,
                    'uploaded_at': profile.updated_at.isoformat()
                }
            
            # Add company associations if any
            if profile.company_associations:
                # Enhance with company data
                for assoc in profile.company_associations:
                    try:
                        company_id = assoc.get('company_id')
                        if company_id:
                            company = CompanyProfile.objects.get(id=company_id)
                            assoc['company_name'] = company.company_name
                            if company.logo_data:
                                assoc['company_logo'] = request.build_absolute_uri(
                                    f'/api/auth/files/company/{company.id}/logo/'
                                )
                    except CompanyProfile.DoesNotExist:
                        pass
                
                data['company_associations'] = profile.company_associations
            
            return Response(data)
        except RecruiterProfile.DoesNotExist:
            # Pre-populate with user data from User table
            initial_data = {
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'email': user.email or '',
            }
            return Response(initial_data)

    def post(self, request, *args, **kwargs):
        print(f"=== RECRUITER ONBOARDING DEBUG ===")
        print(f"Request data: {request.data}")
        print(f"User: {request.user}")
        
        user = request.user
        data = request.data.copy()
        
        # Pre-populate with user data if not provided
        if not data.get('first_name') and user.first_name:
            data['first_name'] = user.first_name
        if not data.get('last_name') and user.last_name:
            data['last_name'] = user.last_name
        if not data.get('email') and user.email:
            data['email'] = user.email
            
        # Handle empty string date fields - convert to None for Django DateField
        date_fields = []  # Add any date fields if needed
        for field in date_fields:
            if field in data and data[field] == '':
                data[field] = None
                print(f"Converted empty string to None for date field: {field}")
        
        # Handle empty string integer fields - convert to None for Django IntegerField
        integer_fields = ['years_of_experience', 'current_company_id']
        for field in integer_fields:
            if field in data and (data[field] == '' or data[field] is None):
                data[field] = None
                print(f"Converted empty value to None for integer field: {field}")
        
        # Handle profile_image field - if it's a URL from file upload, store it in profile_image_url
        if 'profile_image' in data and data['profile_image']:
            if data['profile_image'].startswith('http'):
                # This is an uploaded file URL, store in profile_image_url field
                data['profile_image_url'] = data['profile_image']
                print(f"Set profile_image_url to: {data['profile_image_url']}")
            elif data['profile_image'].startswith('blob:'):
                # This is a blob URL, ignore it since the actual file should be uploaded separately
                print(f"Ignoring blob URL: {data['profile_image']}")
            # Remove the profile_image field since it's not a model field
            del data['profile_image']
            
        # Only one profile per user: update if exists, else create
        try:
            profile = RecruiterProfile.objects.get(user=user)
            serializer = self.get_serializer(profile, data=data, partial=True)
        except RecruiterProfile.DoesNotExist:
            serializer = self.get_serializer(data=data)
        
        print(f"Serializer is valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            
        serializer.is_valid(raise_exception=True)
        profile_obj = serializer.save(user=user)
        
        # Mark profile as complete when successfully saved with minimum required fields
        if profile_obj.first_name and profile_obj.email and profile_obj.job_title:
            profile_obj.is_complete = True
            profile_obj.save(update_fields=['is_complete'])
            print(f"Profile marked as complete: {profile_obj.is_complete}")
        
        # Update User model with profile data
        if profile_obj.first_name and profile_obj.first_name != user.first_name:
            user.first_name = profile_obj.first_name
        if profile_obj.last_name and profile_obj.last_name != user.last_name:
            user.last_name = profile_obj.last_name
        if profile_obj.email and profile_obj.email != user.email:
            user.email = profile_obj.email
        user.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CompanyProfileView(generics.RetrieveUpdateAPIView):
    """Main view for Company Profile operations"""
    serializer_class = CompanyProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = CompanyProfile.objects.all()

    def get_object(self):
        profile, created = CompanyProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            profile = CompanyProfile.objects.get(user=user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except CompanyProfile.DoesNotExist:
            # Return empty data for company profile
            return Response({})

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()
        
        print(f"=== COMPANY ONBOARDING DEBUG ===")
        print(f"Request data: {request.data}")
        print(f"User: {request.user}")
        
        # Handle empty string integer fields - convert to None for Django IntegerField
        integer_fields = ['founded_year']
        for field in integer_fields:
            if field in data and (data[field] == '' or data[field] == None):
                data[field] = None
                print(f"Converted empty value to None for integer field: {field}")
                
        # Handle empty string date fields - convert to None for Django DateField
        date_fields = []  # Add any date fields here if needed
        for field in date_fields:
            if field in data and data[field] == '':
                data[field] = None
                print(f"Converted empty string to None for date field: {field}")
        
        # Handle empty string decimal fields - convert to None for Django DecimalField
        decimal_fields = []  # Add any decimal fields here if needed
        for field in decimal_fields:
            if field in data and data[field] == '':
                data[field] = None
                print(f"Converted empty string to None for decimal field: {field}")
                
        # Only one profile per user: update if exists, else create
        try:
            profile = CompanyProfile.objects.get(user=user)
            serializer = self.get_serializer(profile, data=data, partial=True)
        except CompanyProfile.DoesNotExist:
            serializer = self.get_serializer(data=data)
        
        print(f"Serializer is valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            
        serializer.is_valid(raise_exception=True)
        profile_obj = serializer.save(user=user)
        
        # Mark profile as complete when successfully saved with minimum required fields
        if profile_obj.company_name:
            profile_obj.is_complete = True
            profile_obj.save(update_fields=['is_complete'])
            print(f"Profile marked as complete: {profile_obj.is_complete}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Backward Compatibility Views
class JobSeekerOnboardingView(JobSeekerProfileView):
    """Backward compatibility view - redirects to JobSeekerProfileView"""
    pass


# Company-Recruiter Relationship Views
class CompanyRecruiterInvitationView(APIView):
    """View for creating and managing company-recruiter invitations"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Create a new invitation"""
        # Only company users can create invitations
        if request.user.role != 'company':
            return Response({'error': 'Only company users can create invitations'},
                           status=status.HTTP_403_FORBIDDEN)
        
        data = request.data.copy()
        
        try:
            # Get the company profile of the requesting user
            company = CompanyProfile.objects.get(user=request.user)
            
            # Validate recruiter email
            recruiter_email = data.get('email')
            if not recruiter_email:
                return Response({'error': 'Recruiter email is required'},
                               status=status.HTTP_400_BAD_REQUEST)
                
            # Check if user exists
            try:
                recruiter_user = User.objects.get(email=recruiter_email, role='recruiter')
                recruiter = RecruiterProfile.objects.get(user=recruiter_user)
            except (User.DoesNotExist, RecruiterProfile.DoesNotExist):
                return Response({'error': 'Recruiter not found'},
                               status=status.HTTP_404_NOT_FOUND)
            
            # Check for existing relationship
            existing = CompanyRecruiterRelationship.objects.filter(
                company=company, recruiter=recruiter
            ).first()
            
            if existing:
                if existing.status == 'accepted':
                    return Response({'error': 'Recruiter is already a member of this company'},
                                  status=status.HTTP_400_BAD_REQUEST)
                elif existing.status in ['pending', 'declined']:
                    # Update the existing invitation
                    existing.status = 'pending'
                    existing.invited_at = timezone.now()
                    existing.responded_at = None
                    existing.role = data.get('role', 'recruiter')
                    existing.save()
                    return Response({
                        'message': 'Invitation resent successfully',
                        'invitation_id': existing.id
                    })
            
            # Create new relationship
            relationship = CompanyRecruiterRelationship.objects.create(
                company=company,
                recruiter=recruiter,
                role=data.get('role', 'recruiter'),
                status='pending'
            )
            
            # TODO: Send email notification to the recruiter
            
            return Response({
                'message': 'Invitation sent successfully',
                'invitation_id': relationship.id
            }, status=status.HTTP_201_CREATED)
            
        except CompanyProfile.DoesNotExist:
            return Response({'error': 'Company profile not found'},
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error creating invitation: {str(e)}'},
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request, *args, **kwargs):
        """Get all invitations for a company or recruiter"""
        try:
            if request.user.role == 'company':
                # Company viewing sent invitations
                company = CompanyProfile.objects.get(user=request.user)
                relationships = CompanyRecruiterRelationship.objects.filter(company=company)
                
                result = []
                for rel in relationships:
                    result.append({
                        'id': rel.id,
                        'recruiter_id': rel.recruiter.id,
                        'recruiter_name': rel.recruiter.full_name,
                        'recruiter_email': rel.recruiter.email,
                        'role': rel.role,
                        'status': rel.status,
                        'invited_at': rel.invited_at.isoformat(),
                        'responded_at': rel.responded_at.isoformat() if rel.responded_at else None
                    })
                
                return Response(result)
                
            elif request.user.role == 'recruiter':
                # Recruiter viewing received invitations
                recruiter = RecruiterProfile.objects.get(user=request.user)
                relationships = CompanyRecruiterRelationship.objects.filter(recruiter=recruiter)
                
                result = []
                for rel in relationships:
                    result.append({
                        'id': rel.id,
                        'company_id': rel.company.id,
                        'company_name': rel.company.company_name,
                        'role': rel.role,
                        'status': rel.status,
                        'invited_at': rel.invited_at.isoformat(),
                        'responded_at': rel.responded_at.isoformat() if rel.responded_at else None
                    })
                
                return Response(result)
            else:
                return Response({'error': 'Invalid user role'},
                              status=status.HTTP_400_BAD_REQUEST)
                
        except (CompanyProfile.DoesNotExist, RecruiterProfile.DoesNotExist):
            return Response({'error': 'Profile not found'},
                          status=status.HTTP_404_NOT_FOUND)


class CompanyRecruiterResponseView(APIView):
    """View for responding to company invitations"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, invitation_id, *args, **kwargs):
        """Accept or decline an invitation"""
        if request.user.role != 'recruiter':
            return Response({'error': 'Only recruiters can respond to invitations'},
                          status=status.HTTP_403_FORBIDDEN)
                
        action = request.data.get('action')
        if action not in ['accept', 'decline']:
            return Response({'error': 'Invalid action. Must be "accept" or "decline"'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the recruiter profile
            recruiter = RecruiterProfile.objects.get(user=request.user)
            
            # Get the invitation
            invitation = CompanyRecruiterRelationship.objects.get(
                id=invitation_id, recruiter=recruiter
            )
            
            if invitation.status != 'pending':
                return Response({
                    'error': f'Cannot respond to an invitation with status "{invitation.status}"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the invitation status
            invitation.status = 'accepted' if action == 'accept' else 'declined'
            invitation.responded_at = timezone.now()
            invitation.save()
            
            # If accepting, update the recruiter's company associations
            if action == 'accept':
                current_associations = recruiter.company_associations or []
                
                # Check if this company is already in the associations
                company_exists = False
                for assoc in current_associations:
                    if assoc.get('company_id') == invitation.company.id:
                        company_exists = True
                        assoc['role'] = invitation.role
                        assoc['status'] = 'active'
                        break
                
                if not company_exists:
                    current_associations.append({
                        'company_id': invitation.company.id,
                        'role': invitation.role,
                        'status': 'active',
                        'joined_at': invitation.responded_at.isoformat()
                    })
                
                # Update the recruiter profile
                recruiter.company_associations = current_associations
                
                # If this is the first company, set it as the current company
                if not recruiter.current_company_id:
                    recruiter.current_company_id = invitation.company.id
                
                recruiter.save()
            
            return Response({
                'message': f'Invitation {action}ed successfully',
                'status': invitation.status
            })
            
        except RecruiterProfile.DoesNotExist:
            return Response({'error': 'Recruiter profile not found'},
                          status=status.HTTP_404_NOT_FOUND)
        except CompanyRecruiterRelationship.DoesNotExist:
            return Response({'error': 'Invitation not found'},
                          status=status.HTTP_404_NOT_FOUND)


class RecruiterCompanySelectionView(APIView):
    """View for recruiters to select their active company"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Set the recruiter's active company"""
        if request.user.role != 'recruiter':
            return Response({'error': 'Only recruiters can select a company'},
                          status=status.HTTP_403_FORBIDDEN)
        
        company_id = request.data.get('company_id')
        if not company_id:
            return Response({'error': 'Company ID is required'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the recruiter profile
            recruiter = RecruiterProfile.objects.get(user=request.user)
            
            # Check if the recruiter is associated with this company
            company_associations = recruiter.company_associations or []
            company_found = False
            
            for assoc in company_associations:
                if assoc.get('company_id') == int(company_id) and assoc.get('status') == 'active':
                    company_found = True
                    break
            
            if not company_found:
                return Response({'error': 'You are not associated with this company'},
                              status=status.HTTP_403_FORBIDDEN)
            
            # Check if the company exists
            try:
                company = CompanyProfile.objects.get(id=company_id)
            except CompanyProfile.DoesNotExist:
                return Response({'error': 'Company not found'},
                              status=status.HTTP_404_NOT_FOUND)
            
            # Update the recruiter's current company
            recruiter.current_company_id = int(company_id)
            recruiter.save()
            
            return Response({
                'message': 'Active company updated successfully',
                'company': {
                    'id': company.id,
                    'name': company.company_name
                }
            })
            
        except RecruiterProfile.DoesNotExist:
            return Response({'error': 'Recruiter profile not found'},
                          status=status.HTTP_404_NOT_FOUND)


class RecruiterOnboardingView(generics.GenericAPIView):
    """View for recruiter onboarding - separate from company onboarding"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'recruiter':
            # Create an instance of the view and call its method directly
            view_instance = RecruiterProfileView()
            view_instance.request = request
            view_instance.format_kwarg = getattr(self, 'format_kwarg', None)
            return view_instance.get(request, *args, **kwargs)
        else:
            return Response({'error': 'Invalid user role. Only recruiter users can access this endpoint'}, 
                           status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'recruiter':
            # Create an instance of the view and call its method directly
            view_instance = RecruiterProfileView()
            view_instance.request = request
            view_instance.format_kwarg = getattr(self, 'format_kwarg', None)
            return view_instance.post(request, *args, **kwargs)
        else:
            return Response({'error': 'Invalid user role. Only recruiter users can access this endpoint'}, 
                           status=status.HTTP_400_BAD_REQUEST)


class CompanyOnboardingView(generics.GenericAPIView):
    """View for company onboarding (formerly recruiter-employer onboarding)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'company':
            # Create an instance of the view and call its method directly
            view_instance = CompanyProfileView()
            view_instance.request = request
            view_instance.format_kwarg = getattr(self, 'format_kwarg', None)
            return view_instance.get(request, *args, **kwargs)
        else:
            return Response({'error': 'Invalid user role. Only company users can access this endpoint'}, 
                           status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role == 'company':
            # Create an instance of the view and call its method directly
            view_instance = CompanyProfileView()
            view_instance.request = request
            view_instance.format_kwarg = getattr(self, 'format_kwarg', None)
            return view_instance.post(request, *args, **kwargs)
        else:
            return Response({'error': 'Invalid user role. Only company users can access this endpoint'}, 
                           status=status.HTTP_400_BAD_REQUEST)
