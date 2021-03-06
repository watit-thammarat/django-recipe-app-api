import tempfile
import os

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse("recipe:recipe-list")


def image_upload_url(id):
    return reverse("recipe:recipe-upload-image", args=[id])


def detail_url(id):
    return reverse("recipe:recipe-detail", args=[id])


def sample_tag(user, name="Main course"):
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name="Cinnamon"):
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    defaults = {"title": "Sample Recipe", "time_minutes": 10, "price": 5.00}
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test123"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        sample_recipe(self.user)
        sample_recipe(self.user)
        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by("-id")
        result = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, result.data)

    def test_recipes_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            email="test2@test.com", password="test123"
        )
        sample_recipe(user2)
        sample_recipe(self.user)
        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.filter(user=self.user)
        result = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, result.data)

    def test_view_recipe_detail(self):
        recipe = sample_recipe(self.user)
        recipe.tags.add(sample_tag(self.user))
        recipe.ingredients.add(sample_ingredient(self.user))
        url = detail_url(recipe.id)
        res = self.client.get(url)
        result = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, result.data)

    def test_create_basic_recipe(self):
        payload = {"title": "title", "time_minutes": 30, "price": 5}
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))

    def test_create_recipe_with_tags(self):
        tag1 = sample_tag(self.user, name="tag1")
        tag2 = sample_tag(self.user, name="tag2")
        payload = {
            "title": "title",
            "time_minutes": 30,
            "price": 5,
            "tags": [tag1.id, tag2.id],
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredient(self):
        ingredient1 = sample_ingredient(self.user, name="ingredient1")
        ingredient2 = sample_ingredient(self.user, name="ingredient2")
        payload = {
            "title": "title",
            "time_minutes": 30,
            "price": 5,
            "ingredients": [ingredient1.id, ingredient2.id],
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data["id"])
        ingredients = recipe.ingredients.all()
        self.assertEqual(len(ingredients), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_update_partial_recipe(self):
        recipe = sample_recipe(self.user)
        recipe.tags.add(sample_tag(self.user))
        recipe.ingredients.add(sample_ingredient(self.user))
        tag = Tag.objects.create(user=self.user, name="tag1")
        payload = {"title": "recipe1", "tags": [tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(tag, tags)

    def test_update_full_recipe(self):
        recipe = sample_recipe(self.user)
        tag = recipe.tags.add(sample_tag(self.user))
        ingredient = recipe.ingredients.add(sample_ingredient(self.user))
        payload = {"title": "recipe1", "time_minutes": 100, "price": 200}
        url = detail_url(recipe.id)
        self.client.put(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.price, payload["price"])
        self.assertEqual(recipe.time_minutes, payload["time_minutes"])
        tags = recipe.tags.all()
        ingredients = recipe.ingredients.all()
        self.assertEqual(len(tags), 0)
        self.assertNotIn(tag, tags)
        self.assertEqual(len(ingredients), 0)
        self.assertNotIn(ingredient, ingredients)


class RecipeImageUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test123"
        )
        self.client.force_authenticate(self.user)
        self.recipe = Recipe.objects.create(
            user=self.user, title="recipe1", price=10, time_minutes=10
        )

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_valid_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
            self.recipe.refresh_from_db()
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertIn("image", res.data)
            self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_invalid_image(self):
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {"image": "notimage"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipe_by_tags(self):
        tag1 = sample_tag(self.user, name="tag1")
        tag2 = sample_tag(self.user, name="tag2")
        recipe1 = sample_recipe(self.user, title="recipe1")
        recipe2 = sample_recipe(self.user, title="recipe2")
        sample_recipe(self.user, title="recipe3")
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        res = self.client.get(RECIPE_URL, {"tags": f"{tag1.id},{tag2.id}"})
        recipes = Recipe.objects.filter(
            id__in=[recipe1.id, recipe2.id]
        ).order_by("-id")
        recipes_json = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, recipes_json.data)

    def test_filter_recipe_by_ingredients(self):
        ingredient1 = sample_ingredient(self.user, name="ingredient1")
        ingredient2 = sample_ingredient(self.user, name="ingredient2")
        recipe1 = sample_recipe(self.user, title="recipe1")
        recipe2 = sample_recipe(self.user, title="recipe2")
        sample_recipe(self.user, title="recipe3")
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        res = self.client.get(
            RECIPE_URL, {"ingredients": f"{ingredient1.id},{ingredient2.id}"}
        )
        recipes = Recipe.objects.filter(
            id__in=[recipe1.id, recipe2.id]
        ).order_by("-id")
        recipes_json = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, recipes_json.data)
