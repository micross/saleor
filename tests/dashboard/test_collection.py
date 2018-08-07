import json
from unittest import mock

from django.urls import reverse
from saleor.dashboard.collection.forms import CollectionForm
from saleor.product.models import Collection

from ..utils import get_redirect_location


def test_list_view(admin_client, collection):
    response = admin_client.get(reverse('dashboard:collection-list'))
    assert response.status_code == 200
    context = response.context
    assert list(context['collections']) == [collection]


def test_collection_form_name():
    data = {'name': 'Test Collection', 'products': []}
    form = CollectionForm(data)
    assert form.is_valid()

    collection = form.save()
    assert collection.slug == 'test-collection'

    invalid_form = CollectionForm()
    assert not invalid_form.is_valid()


def test_collection_form_with_products(product):
    data = {'name': 'Test collection', 'products': [product.id]}
    form = CollectionForm(data)
    assert form.is_valid()

    collection = form.save()
    assert collection.products.count() == 1


def test_collection_create_view(admin_client):
    response = admin_client.get(reverse('dashboard:collection-add'))
    assert response.status_code == 200

    data = {'name': 'Test'}
    response = admin_client.post(reverse('dashboard:collection-add'), data)
    assert response.status_code == 302

    redirected_url = get_redirect_location(response)
    assert redirected_url == reverse('dashboard:collection-list')


def test_collection_update_view(admin_client, collection, product):
    url = reverse('dashboard:collection-update', kwargs={'pk': collection.id})
    response = admin_client.get(url)
    assert response.status_code == 200

    current_name = collection.name
    data = {'name': 'New name', 'products': [product.id]}
    response = admin_client.post(url, data)
    assert response.status_code == 302

    collection.refresh_from_db()
    assert not current_name == collection.name
    assert list(collection.products.all()) == [product]


@mock.patch('saleor.dashboard.collection.views.get_menus_that_needs_update')
@mock.patch('saleor.dashboard.collection.views.update_menus')
def test_collection_delete_view(
        mock_update_menus, mock_get_menus, admin_client, collection):
    # Test Http404 when collection doesn't exist
    url404 = reverse('dashboard:collection-delete', kwargs={'pk': 123123})
    response404 = admin_client.post(url404)
    assert response404.status_code == 404

    # Test deleting object
    collections_count = Collection.objects.count()
    url = reverse('dashboard:collection-delete', kwargs={'pk': collection.id})
    mock_get_menus.return_value = [collection.id]
    response = admin_client.post(url)
    assert response.status_code == 302
    mock_update_menus.assert_called_once_with([collection.pk])

    assert Collection.objects.count() == (collections_count - 1)


@mock.patch('saleor.dashboard.collection.views.get_menus_that_needs_update')
@mock.patch('saleor.dashboard.collection.views.update_menus')
def test_collection_delete_view_menus_not_updated(
        mock_update_menus, mock_get_menus, admin_client, collection):
    url = reverse('dashboard:collection-delete', kwargs={'pk': collection.id})
    mock_get_menus.return_value = []
    response = admin_client.post(url)
    assert response.status_code == 302
    assert mock_get_menus.called
    assert not mock_update_menus.called


def test_collection_is_published_toggle_view(db, admin_client, collection):
    url = reverse('dashboard:collection-publish', kwargs={'pk': collection.pk})
    response = admin_client.post(url)
    assert response.status_code == 200
    data = {'success': True, 'is_published': False}
    assert json.loads(response.content.decode('utf8')) == data
    admin_client.post(url)
    collection.refresh_from_db()
    assert collection.is_published