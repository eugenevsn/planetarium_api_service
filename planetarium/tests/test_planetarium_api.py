import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from planetarium.models import AstronomyShow, PlanetariumDome, ShowSession, ShowTheme
from planetarium.serializers import (
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
)

ASTRONOMY_SHOW_URL = reverse("planetarium:astronomyshow-list")
SHOW_SESSION_URL = reverse("planetarium:showsession-list")


def create_sample_astronomy_show(**params):
    defaults = {"title": "Sample astronomy show", "description": "Sample description"}
    defaults.update(params)
    return AstronomyShow.objects.create(**defaults)


def create_sample_show_session(**params):
    planetarium_dome = PlanetariumDome.objects.create(name="Blue", rows=20, seats_in_row=20)
    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "astronomy_show": None,
        "planetarium_dome": planetarium_dome,
    }
    defaults.update(params)
    return ShowSession.objects.create(**defaults)


def get_image_upload_url(astronomy_show_id):
    return reverse("planetarium:astronomyshow-upload-image", args=[astronomy_show_id])


def get_detail_url(astronomy_show_id):
    return reverse("planetarium:astronomyshow-detail", args=[astronomy_show_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authentication_required(self):
        res = self.client.get(ASTRONOMY_SHOW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAstronomyShowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@test.com", "testpass")
        self.client.force_authenticate(self.user)

    def test_list_astronomy_show(self):
        create_sample_astronomy_show()
        create_sample_astronomy_show()
        res = self.client.get(ASTRONOMY_SHOW_URL)
        astronomy_shows = AstronomyShow.objects.order_by("id")
        serializer = AstronomyShowListSerializer(astronomy_shows, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_astronomy_shows_by_show_theme(self):
        show_theme1 = ShowTheme.objects.create(name="Show Theme 1")
        show_theme2 = ShowTheme.objects.create(name="Show Theme 2")
        astronomy_show1 = create_sample_astronomy_show(title="Astronomy Show 1")
        astronomy_show2 = create_sample_astronomy_show(title="Astronomy Show 2")
        astronomy_show1.show_theme.add(show_theme1)
        astronomy_show2.show_theme.add(show_theme2)
        astronomy_show3 = create_sample_astronomy_show(title="Astronomy show without show themes")
        res = self.client.get(
            ASTRONOMY_SHOW_URL, {"show_theme": f"{show_theme1.id},{show_theme2.id}"}
        )
        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)
        self.assertIn(str(serializer1.data), [str(item) for item in res.data["results"]])
        self.assertIn(str(serializer2.data), [str(item) for item in res.data["results"]])
        self.assertNotIn(str(serializer3.data), [str(item) for item in res.data["results"]])

    def test_filter_astronomy_shows_by_title(self):
        astronomy_show1 = create_sample_astronomy_show(title="Astronomy Show")
        create_sample_astronomy_show(title="Another Astronomy Show")
        create_sample_astronomy_show(title="No match")
        res = self.client.get(ASTRONOMY_SHOW_URL, {"title": "Astronomy Show"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(res.data["results"][0]["title"], astronomy_show1.title)

    def test_retrieve_astronomy_show_detail(self):
        astronomy_show = create_sample_astronomy_show()
        astronomy_show.show_theme.add(ShowTheme.objects.create(name="Show Theme"))
        url = get_detail_url(astronomy_show.id)
        res = self.client.get(url)
        serializer = AstronomyShowDetailSerializer(astronomy_show)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminAstronomyShowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("admin@admin.com", "testpass", is_staff=True)
        self.client.force_authenticate(self.user)

    def test_create_astronomy_show(self):
        payload = {"title": "Movie", "description": "Description"}
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(astronomy_show, key))

    def test_create_astronomy_show_with_show_theme(self):
        show_theme1 = ShowTheme.objects.create(name="Journey")
        show_theme2 = ShowTheme.objects.create(name="Stars")
        payload = {
            "title": "To infinity and beyond",
            "show_theme": [show_theme1.id, show_theme2.id],
            "description": "Traveling through space and time",
        }
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(id=res.data["id"])
        show_theme = astronomy_show.show_theme.all()
        self.assertEqual(show_theme.count(), 2)
        self.assertIn(show_theme1, show_theme)
        self.assertIn(show_theme2, show_theme)

    def test_retrieve_astronomy_show_detail_unauthorized(self):
        astronomy_show = create_sample_astronomy_show()
        self.client.force_authenticate(user=None)
        url = get_detail_url(astronomy_show.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_astronomy_show_invalid(self):
        payload = {"title": ""}
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AstronomyShowImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("admin@myproject.com", "password")
        self.client.force_authenticate(self.user)
        self.astronomy_show = create_sample_astronomy_show()
        self.show_session = create_sample_show_session(astronomy_show=self.astronomy_show)

    def tearDown(self):
        self.astronomy_show.image.delete()

    def test_upload_image_to_astronomy_show(self):
        url = get_image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.astronomy_show.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.astronomy_show.image.path))

    def test_upload_image_bad_request(self):
        url = get_image_upload_url(self.astronomy_show.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_astronomy_show_list_should_not_work(self):
        url = ASTRONOMY_SHOW_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {"title": "Title", "description": "Description", "image": ntf},
                format="multipart",
            )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(title="Title")
        self.assertFalse(astronomy_show.image)

    def test_image_url_is_shown_on_astronomy_show_detail(self):
        url = get_image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(get_detail_url(self.astronomy_show.id))
        self.assertIn("image", res.data)

    def test_put_astronomy_show_not_allowed(self):
        payload = {"title": "New astronomy show", "description": "New description"}
        astronomy_show = create_sample_astronomy_show()
        url = get_detail_url(astronomy_show.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_astronomy_show_not_allowed(self):
        astronomy_show = create_sample_astronomy_show()
        url = get_detail_url(astronomy_show.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
