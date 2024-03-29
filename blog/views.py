from typing import Any
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Post, Category, Tag, Comment, ReComment
from django.core.exceptions import PermissionDenied
from django.utils.text import slugify
from django.urls import reverse_lazy
from django.db.models import Q
from .forms import CommentForm, ReCommentForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse


class PostList(ListView):
    model = Post
    ordering = "-pk"
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data()
        context["categories"] = Category.objects.all()
        context["no_category_post_count"] = Post.objects.filter(category=None).count()
        context["paginate_by"] = self.paginate_by
        return context


class PostDetail(DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data()
        context["categories"] = Category.objects.all()
        context["no_category_post_count"] = Post.objects.filter(category=None).count()
        context["comment_form"] = CommentForm
        context["recomment_form"] = ReCommentForm()
        return context

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        post = Post.objects.get(pk=pk)
        post.view_count += 1
        post.save()
        return super().get_object(queryset)


class PostCreate(LoginRequiredMixin, CreateView):
    model = Post
    fields = [
        "title",
        "hook_text",
        "content",
        "thumbnail_image",
        "file_upload",
        "category",
    ]

    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated:
            form.instance.author = current_user
            response = super(PostCreate, self).form_valid(form)

            tags_str = self.request.POST.get("tags_str")
            if tags_str:
                tags_str = tags_str.strip()
                tags_str = tags_str.strip("; ")

                tags_str = tags_str.replace(",", ";")
                tags_list = tags_str.split("; ")
                for t in tags_list:
                    t = t.strip()
                    tag, is_tag_created = Tag.objects.get_or_create(name=t)
                    if is_tag_created:
                        tag.slug = slugify(t, allow_unicode=True)
                        tag.save()
                    self.object.tags.add(tag)
            return response
        else:
            return redirect(reverse("root"))


class PostUpdate(LoginRequiredMixin, UpdateView):
    model = Post
    fields = [
        "title",
        "hook_text",
        "content",
        "thumbnail_image",
        "file_upload",
        "category",
    ]

    template_name = "blog/post_update_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(PostUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(PostUpdate, self).get_context_data()
        if self.object.tags.exists():
            tags_str_list = list()
            for t in self.object.tags.all():
                tags_str_list.append(t.name)
            context["tags_str_default"] = "; ".join(tags_str_list)
        return context

    def form_valid(self, form):
        response = super(PostUpdate, self).form_valid(form)
        self.object.tags.clear()

        tags_str = self.request.POST.get("tags_str")
        if tags_str:
            tags_str = tags_str.strip()
            tags_str = tags_str.strip("; ")

            tags_str = tags_str.replace(",", ";")
            tags_list = tags_str.split(";")

            for t in tags_list:
                t = t.strip()
                tag, is_tag_created = Tag.objects.get_or_create(name=t)
                if is_tag_created:
                    tag.slug = slugify(t, allow_unicode=True)
                    tag.save()
                self.object.tags.add(tag)
        return response


def category_page(request, slug):
    if slug == "no_category":
        category = "미분류"
        post_list = Post.objects.filter(category=None)
    else:
        category = Category.objects.get(slug=slug)
        post_list = Post.objects.filter(category=category)

    return render(
        request,
        "blog/post_list.html",
        {
            "post_list": post_list,
            "categories": Category.objects.all(),
            "no_category_post_count": Post.objects.filter(category=None).count(),
            "category": category,
        },
    )


def tag_page(request, slug):
    tag = Tag.objects.get(slug=slug)
    post_list = tag.post_set.all()

    return render(
        request,
        "blog/post_list.html",
        {
            "post_list": post_list,
            "tag": tag,
            "categories": Category.objects.all(),
            "no_category_post_count": Post.objects.filter(category=None).count(),
        },
    )


class PostDelete(DeleteView):
    model = Post
    success_url = reverse_lazy("post_list")

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class PostSearch(PostList):
    paginate_by = None

    def get_queryset(self):
        q = self.kwargs["q"]
        post_list = Post.objects.filter(
            Q(title__icontains=q) | Q(tags__name__icontains=q)
        ).distinct()
        return post_list

    def get_context_data(self, **kwargs):
        context = super(PostSearch, self).get_context_data()
        q = self.kwargs["q"]
        context["search_info"] = f"Search: {q} ({self.get_queryset().count()})"
        return context


def create_comment(request, pk):
    if request.user.is_authenticated:
        post = get_object_or_404(Post, pk=pk)

        if request.method == "POST":
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                return redirect(comment.get_absolute_url())
        else:
            return redirect(post.get_absolute_url())
    else:
        raise PermissionDenied


class CommentUpdate(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(CommentUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied


def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    post = comment.post
    if request.user.is_authenticated and request.user == comment.author:
        comment.delete()
        return redirect(post.get_absolute_url())
    else:
        raise PermissionDenied


def create_recomment(request, pk):
    filled_form = ReCommentForm(request.POST)

    if filled_form.is_valid():
        recomment = filled_form.save(commit=False)
        recomment.author = request.user
        recomment.comment_id = request.POST.get("comment")
        recomment.save()

    return redirect("post_detail", pk)


class ReCommentUpdate(LoginRequiredMixin, UpdateView):
    model = ReComment
    form_class = ReCommentForm

    def get_success_url(self):
        post_pk = self.object.comment.post.pk
        return reverse("post_detail", kwargs={"pk": post_pk})

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(ReCommentUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied


@login_required
def delete_recomment(request, pk):
    recomment = get_object_or_404(ReComment, pk=pk)
    post = recomment.comment.post
    if request.user == recomment.author:
        recomment.delete()
        return redirect(post.get_absolute_url())
    else:
        raise PermissionDenied
