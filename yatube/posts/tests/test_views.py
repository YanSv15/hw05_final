
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.cache import cache

from http import HTTPStatus

from ..models import Group, Post, Follow

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовое название сообщества',
            slug='test-slug',
            description='Тестовое описание сообщества',
        )
        cls.user = User.objects.create_user(
            username='user')
        cls.user_author = User.objects.create_user(
            username='user_author')

        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.user = User.objects.create_user(username='YanchikS')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()
        self.post_author = Client()
        self.post_author.force_login(self.user_author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html':
            reverse('posts:index'),
            'posts/group_list.html':
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            'posts/profile.html':
            reverse('posts:profile', kwargs={'username': self.user}),
            'posts/post_detail.html':
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
            'posts/create_post.html':
            reverse('posts:post_create'),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        post_detail_url = reverse('posts:post_detail',
                                  kwargs={'post_id': self.post.id})
        response = self.authorized_client.get(post_detail_url)
        first_obj = response.context['post']
        post_author = first_obj.author
        post_text = first_obj.text
        post_group = first_obj.group
        self.assertEqual(post_author, self.post.author)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_group, self.post.group)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:index'))
        post_one = response.context['page_obj'][0]
        post_author = post_one.author
        post_text = post_one.text
        self.assertEqual(post_author, self.post.author)
        self.assertEqual(post_text, 'Тестовая запись')

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:group_list',
                                                 kwargs={'slug': 'test-slug'}))
        group_one = response.context['group']
        group_title = group_one.title
        group_slug = group_one.slug
        group_description = group_one.description
        self.assertEqual(group_title, 'Тестовое название сообщества')
        self.assertEqual(group_slug, 'test-slug')
        self.assertEqual(group_description, 'Тестовое описание сообщества')

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['author'], self.user)

    def test_post_create_page_show_correct_context(self):
        """Форма создаваемого поста в шаблоне create_post.html
        сформирована с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_additional_verification_in_another_page(self):
        """Дополнительная проверка для указании группы поста,
        пост появляется на других страницах."""
        post = Post.objects.create(
            text='Тестовый пост',
            author=self.user,
            group=self.group)
        form_fields = {
            reverse(
                'posts:index'): post,
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}): post,
            reverse(
                'posts:profile',
                kwargs={'username': self.user}): post,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context.get('page_obj')
                self.assertIn(expected, form_field)

    def test_post_create_additional_verification_not_in_another_group(self):
        """Дополнительная проверка, чтобы пост не попал в группу,
        для которой не предназначен"""
        form_fields = {
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}):
            Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context.get('page_obj')
                self.assertNotIn(expected, form_field)

    def test_guest_user_create_post(self):
        """Дополнительная проверка при создании записи
        не авторизированным пользователем."""
        posts_count = Post.objects.count()
        form_fields = {
            'text': 'Тестовый текст',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_fields,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_nonauthor_post_edit(self):
        """Дополнительная проверка при редактировании записи
        не автором записи."""
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.user_author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.latest('id')
        self.assertFalse(post.text == form_data['text'])
        self.assertFalse(post.author == self.post_author)
        self.assertTrue(post.group_id == form_data['group'])

    def test_cache_index_page(self):
        """Проверка работы кеша"""
        post = Post.objects.create(
            text='Пост кеш',
            author=self.user)
        content_add = self.authorized_client.get(
            reverse('posts:index')).content
        post.delete()
        content_delete = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(content_add, content_delete)
        cache.clear()
        content_cache_clear = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(content_add, content_cache_clear)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='test-user',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.posts = []
        for i in range(0, 13):
            cls.posts.append(
                Post(
                    author=cls.user,
                    text=f'Test post {i} for verification',
                    group=cls.group,
                )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def paginator_test(self):
        post_count = Post.objects.count()
        paginator_amount = 10
        second_page_amount = post_count + 3
        posts = [
            Post(
                text=f'Текст поста {1}', author=PaginatorViewsTest.user,
                group=PaginatorViewsTest.group
            ) for num in range(1, paginator_amount + second_page_amount)
        ]
        Post.objects.bulk_create(posts)

        pages = (
            (1, paginator_amount),
            (2, second_page_amount)
        )
        for value in pages:
            with self.subTest(value=value):
                response_page_1 = self.authorized_client.get(value)
                response_page_2 = self.authorized_client.get(value + '?page=2')
                self.assertEqual(len(response_page_1.context['page_obj']), 10)
                self.assertEqual(len(response_page_2.context['page_obj']), 3)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create(
            username='post_autor',
        )
        cls.post_follower = User.objects.create(
            username='post_follower',
        )
        cls.post = Post.objects.create(
            text='Подписаться',
            author=cls.post_autor,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_autor)

    def test_follow_on_user(self):
        """Проверка подписки."""
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post_follower}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author_id, self.post_follower.id)
        self.assertEqual(follow.user_id, self.post_autor.id)

    def test_unfollow_on_user(self):
        """Проверка отписки."""
        Follow.objects.create(
            user=self.post_autor,
            author=self.post_follower)
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post_follower}))
        self.assertEqual(Follow.objects.count(), count_follow - 1)

    def test_follow_on_authors(self):
        """Проверка новых записей в ленте тех, кто подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подписаться")
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        """Проверка новых записей в ленте тех, кто не подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подписаться")
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'].object_list)
