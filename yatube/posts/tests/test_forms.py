from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_groups = {}
        for i in range(2):
            index = i + 1
            cls.new_groups[index] = Group.objects.create(
                title=f'Тестовая группа {index}',
                slug=f'test_group{index}',
                description=f'Тестовое описание группы {index}'
            )
        cls.user = User.objects.create_user(username='TestUser')
        cls.new_post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_auth(self):
        posts_count = Post.objects.count()
        required_group = self.new_groups[list(self.new_groups.keys())[0]]
        form_data = {
            'text': 'Тестовый текст из формы',
            'group': required_group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': self.user.username})
                             )
        posts_amount = Post.objects.count()
        new_post = Post.objects.get(pk=posts_amount)
        self.assertEqual(posts_amount, posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                pk=new_post.pk
            ).exists()
        )

    def test_edit_post_auth(self):
        required_group = self.new_groups[list(self.new_groups.keys())[1]]
        form_data = {
            'text': 'Новый текст для поста',
            'group': required_group.pk
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.new_post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.new_post.pk})
                             )
        self.assertEqual(Post.objects.get(pk=self.new_post.pk).text,
                         form_data[list(form_data.keys())[0]])
        self.assertEqual(Post.objects.get(pk=self.new_post.pk).group.pk,
                         form_data[list(form_data.keys())[1]])

    def test_create_post_guest(self):
        posts_count = Post.objects.count()
        required_group = self.new_groups[list(self.new_groups.keys())[0]]
        form_data = {
            'text': 'Тестовый текст из формы',
            'group': required_group.pk
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             f'{reverse("users:login")}?next='
                             f'{reverse("posts:post_create")}'
                             )
        posts_amount = Post.objects.count()
        self.assertEqual(posts_amount, posts_count)

    def test_edit_post_guest(self):
        required_group = self.new_groups[list(self.new_groups.keys())[1]]
        form_data = {
            'text': 'Новый текст для поста',
            'group': required_group.pk
        }
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.new_post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '{}?next={}'.format(
            reverse("users:login"),
            reverse("posts:post_edit",kwargs={"post_id": self.new_post.pk})
        ))
        self.assertNotEqual(Post.objects.get(pk=self.new_post.pk).text,
                            form_data[list(form_data.keys())[0]])
        try:
            self.assertNotEqual(Post.objects.get(pk=self.new_post.pk).group.pk,
                                form_data[list(form_data.keys())[1]])
        except AttributeError:
            self.assertIsNone(Post.objects.get(pk=self.new_post.pk).group)
