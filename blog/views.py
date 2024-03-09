from typing import Any
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
from .models import Post, Category, Tag
from django.core.exceptions import PermissionDenied
from django.utils.text import slugify
from django.urls import reverse_lazy
from django.db.models import Q


class PostList(ListView):
    model = Post
    ordering = "-pk"

    def get_context_data(self, **kwargs):
        context = super(PostList, self).get_context_data()
        context["categories"] = Category.objects.all()
        context["no_category_post_count"] = Post.objects.filter(category=None).count()
        return context


class PostDetail(DetailView):
    model = Post

    def get_context_data(self, **kwargs):
        context = super(PostDetail, self).get_context_data()
        context["categories"] = Category.objects.all()
        context["no_category_post_count"] = Post.objects.filter(category=None).count()
        return context


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
            return redirect("/blog/")


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
