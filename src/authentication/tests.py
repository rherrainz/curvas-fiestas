from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LoginToken


class AuthenticationFlowTests(TestCase):
    def test_login_request_preserves_safe_next_in_magic_link(self):
        response = self.client.post(
            reverse("authentication:login_request"),
            {
                "email": "test@laanonima.com.ar",
                "next": "/sales/curves/?region=1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/auth/verify/",
        )
        self.assertContains(
            response,
            "next=%2Fsales%2Fcurves%2F%3Fregion%3D1",
        )

    def test_verify_token_redirects_to_safe_next(self):
        user = User.objects.create_user(
            username="test@laanonima.com.ar",
            email="test@laanonima.com.ar",
        )
        token = LoginToken.objects.create(
            email=user.email,
            token="safe-token",
            user=user,
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.client.get(
            reverse("authentication:verify_token", kwargs={"token": token.token}),
            {"next": "/stock/curves/"},
        )

        self.assertRedirects(response, "/stock/curves/")

    def test_verify_token_rejects_external_next(self):
        user = User.objects.create_user(
            username="test2@laanonima.com.ar",
            email="test2@laanonima.com.ar",
        )
        token = LoginToken.objects.create(
            email=user.email,
            token="unsafe-token",
            user=user,
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.client.get(
            reverse("authentication:verify_token", kwargs={"token": token.token}),
            {"next": "https://evil.example/phish"},
        )

        self.assertRedirects(response, reverse("home"))
