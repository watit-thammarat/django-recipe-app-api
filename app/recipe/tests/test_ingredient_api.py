from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse("recipe:ingredient-list")


class PublicIngredientApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "test@test.com", "test123"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        Ingredient.objects.create(user=self.user, name="test1")
        Ingredient.objects.create(user=self.user, name="test2")
        res = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            "test2@test.com", "test123"
        )
        Ingredient.objects.create(user=user2, name="ingredient1")
        ingredient = Ingredient.objects.create(
            user=self.user, name="ingredient2"
        )
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)

    def test_create_ingredient_successfull(self):
        payload = {"name": "test"}
        res = self.client.post(INGREDIENTS_URL, payload)
        exists = Ingredient.objects.filter(
            name=payload["name"], user=self.user
        ).exists()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        payload = {"name": ""}
        res = self.client.post(INGREDIENTS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
