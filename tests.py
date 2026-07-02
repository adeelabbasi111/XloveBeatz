"""
Basic test suite.
Run: python -m pytest tests.py -v
"""
import json
import pytest
from app import create_app
from helpers.config import Config
from helpers.models import db, User


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---- Health ----

class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['status'] == 'online'


# ---- Public ----

class TestPublic:
    def test_homepage(self, client):
        assert client.get('/').status_code == 200

    def test_player(self, client):
        assert client.get('/player').status_code == 200

    def test_missing_beat_redirects(self, client):
        assert client.get('/beat/nope').status_code == 302


# ---- Auth ----

class TestAuth:
    def test_signup_page(self, client):
        assert client.get('/signup').status_code == 200

    def test_login_page(self, client):
        assert client.get('/login').status_code == 200

    def test_api_signup_success(self, client):
        resp = client.post('/api/auth/signup',
                           data=json.dumps(dict(
                               username='test', email='t@t.com',
                               password='pass123', confirm_password='pass123')),
                           content_type='application/json')
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_api_signup_password_mismatch(self, client):
        resp = client.post('/api/auth/signup',
                           data=json.dumps(dict(
                               username='test', email='t@t.com',
                               password='pass123', confirm_password='xxx')),
                           content_type='application/json')
        assert resp.status_code == 400

    def test_api_login_bad_credentials(self, client):
        resp = client.post('/api/auth/login',
                           data=json.dumps(dict(email='x@x.com', password='nope')),
                           content_type='application/json')
        assert resp.status_code == 401

    def test_logout(self, client):
        resp = client.post('/api/auth/logout')
        assert json.loads(resp.data)['success'] is True


# ---- Cart ----

class TestCart:
    def test_cart_page(self, client):
        assert client.get('/cart').status_code == 200

    def test_add_invalid_product(self, client):
        resp = client.post('/cart/add', data={'product_id': 99999, 'quantity': 1})
        assert resp.status_code == 302


# ---- Admin ----

class TestAdmin:
    def test_requires_login(self, client):
        assert client.get('/admin').status_code == 302

    def test_requires_admin(self, client, app):
        with app.app_context():
            from werkzeug.security import generate_password_hash
            u = User(username='u', email='u@u.com',
                     password_hash=generate_password_hash('p'), is_admin=False)
            db.session.add(u)
            db.session.commit()

        client.post('/login', data={'email': 'u@u.com', 'password': 'p'})
        assert client.get('/admin').status_code == 302


# ---- API auth/me ----

class TestAPIMe:
    def test_logged_out(self, client):
        data = json.loads(client.get('/api/auth/me').data)
        assert data['logged_in'] is False


# ---- Pagination ----

class TestPagination:
    def test_admin_products_pagination(self, client, app):
        with app.app_context():
            from werkzeug.security import generate_password_hash
            u = User(username='admin2', email='a2@a.com',
                     password_hash=generate_password_hash('p'), is_admin=True)
            db.session.add(u)
            db.session.commit()

        client.post('/login', data={'email': 'a2@a.com', 'password': 'p'})
        resp = client.get('/admin/products?page=1')
        assert resp.status_code == 200