from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import Recipe, Category
from .forms import RecipeForm, CategoryForm, ReviewForm
from django.contrib.auth import logout
from .forms import ProfileForm
from .models import UserProfile
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str


def home(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', None)
    chef = request.GET.get('chef', None)

    if query:
        recipes = Recipe.objects.filter(title__icontains=query)
    elif category:
        recipes = Recipe.objects.filter(categories__id=category)
    elif chef:
        recipes = Recipe.objects.filter(chef__user__email=chef)
    else:
        recipes = Recipe.objects.all()

    categories = Category.objects.all()
    top_chefs = UserProfile.objects.all()[:3]

    selected_category = None
    if category:
        selected_category = Category.objects.filter(id=category).first()

    selected_chef = None
    if chef:
        selected_chef = UserProfile.objects.filter(user__email=chef).first()

    message = None
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            message = "You have successfully subscribed to our newsletter!"

    return render(request, 'home.html', {
        'recipes': recipes,
        'query': query,
        'categories': categories,
        'top_chefs': top_chefs,
        'selected_category': selected_category,
        'selected_chef': selected_chef,
    })


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # If UserProfile doesn't exist, create it for the user
        user_profile = UserProfile(user=request.user)
        user_profile.save()

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to the profile page after updating
    else:
        form = ProfileForm(instance=user_profile)

    return render(request, 'profile.html', {'form': form, 'user_profile': user_profile})

@login_required
def profile_edit(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # If UserProfile doesn't exist, create it for the user
        user_profile = UserProfile(user=request.user)
        user_profile.save()

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')  # After saving, redirect to the profile view
    else:
        form = ProfileForm(instance=user_profile)

    return render(request, 'edit_profile.html', {'form': form, 'user_profile': user_profile})

@login_required
def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)  # Pass request.FILES to handle image upload
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.created_by = request.user
            recipe.save()
            return redirect('home')
    else:
        form = RecipeForm()
    return render(request, 'add_recipe.html', {'form': form})

@login_required
def update_recipe(request, pk):
    try:
        recipe = Recipe.objects.get(id=pk)
    except Recipe.DoesNotExist:
        raise Http404("Recipe not found")

    # Form handling logic
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        if form.is_valid():
            form.save()
            return redirect('recipe_detail', id=recipe.id)
    else:
        form = RecipeForm(instance=recipe)

    return render(request, 'update_recipe.html', {'form': form, 'recipe': recipe})


@login_required
def delete_recipe(request, pk):
    recipe = Recipe.objects.get(pk=pk, created_by=request.user)
    recipe.delete()
    return redirect('home')

@login_required
def recipe_detail(request, id):
    recipe = get_object_or_404(Recipe, id=id)
    reviews = Review.objects.filter(recipe=recipe).order_by('-created_at')

    if request.method == 'POST':
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.recipe = recipe
            review.user = request.user
            review.save()
            return redirect('recipe_detail', id=recipe.id)
    else:
        review_form = ReviewForm()

    return render(request, 'recipe_detail.html', {
        'recipe': recipe,
        'reviews': reviews,
        'review_form': review_form,
    })

def logout_view(request):
    if request.method in ['POST', 'GET']:
        logout(request)
        return redirect('home')

def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'add_category.html', {'form': form})

def category_list(request):
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories})

def update_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'update_category.html', {'form': form})

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        category.delete()
        return redirect('category_list')


from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Recipe, Review
from .forms import ReviewForm

# Add a review to a recipe
@login_required
def add_review(request, id):
    recipe = get_object_or_404(Recipe, id=id)

    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return redirect('login')  # Redirect to login if not authenticated

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            # Create the review and associate it with the recipe and user
            review = form.save(commit=False)
            review.recipe = recipe
            review.user = request.user
            review.save()
            return redirect('recipe_detail', id=recipe.id)  # Redirect to the recipe detail page
    else:
        form = ReviewForm()

    return render(request, 'add_review.html', {'form': form, 'recipe': recipe})
