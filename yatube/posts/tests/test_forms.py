import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post, Comment
from posts.forms import PostForm


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(
            username='post_author')
        cls.comm_author = User.objects.create_user(
            username='comm_author')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.form = PostForm()
        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.post_author,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)
        self.auth_user_comm = Client()
        self.auth_user_comm.force_login(self.comm_author)
        cache.clear()

    def test_authorized_user_create_post(self):
        """Проверка создания записи авторизированным пользователем."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data['group'])
        self.assertEqual(post.image.name, 'posts/small.gif')

    def test_authorized_user_edit_post(self):
        """Проверка редактирования записи авторизированным пользователем."""
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author)
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id}
        response = self.authorized_user.post(
            reverse(
                'posts:edit',
                args=[post.id]),
            data=form_data,
            follow=True)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id}))
        post_one = Post.objects.latest('id')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post_one.text, form_data['text'])
        self.assertEqual(post_one.author, self.post_author)
        self.assertEqual(post_one.group_id, form_data['group'])

    def test_authorized_user_create_comment(self):
        """Проверка комментирования авторизованным пользователем."""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Текст поста для комментирования',
            author=self.post_author)
        form_data = {'text': 'Тестовый коментарий'}
        response = self.auth_user_comm.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=True)
        comment = Comment.objects.latest('id')
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.comm_author)
        self.assertEqual(comment.post_id, post.id)
        self.assertRedirects(
            response, reverse('posts:post_detail', args={post.id}))

    def test_create_post(self):
        """Дополнительная проверка на загрузку не изображения."""
        image = SimpleUploadedFile(
            name='test_image.py',
            content=open('static/img/test_image/image.py', 'rb').read(),
            content_type='text/py'
        )
        form_data = {
            'text': 'Новый тестовый текст',
            'group': self.group.pk,
            'image': image
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertFormError(
            response,
            'form',
            'image',
            'Загрузите правильное изображение. '
            'Файл, который вы загрузили, поврежден или не '
            'является изображением.'
        )
