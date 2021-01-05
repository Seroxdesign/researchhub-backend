from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.crypto import get_random_string

from .models import Paper, Vote


@receiver(post_save, sender=Paper, dispatch_uid='add_paper_slug')
def add_paper_slug(
    sender,
    instance,
    created,
    update_fields,
    **kwargs
):
    if created:
        suffix = get_random_string(length=32)
        paper_title = instance.paper_title
        title = instance.title

        slug = paper_title or title
        slug = slugify(slug)
        if not slug:
            slug += suffix
        instance.slug = slug
        instance.save()


@receiver(post_save, sender=Vote, dispatch_uid='recalculate_paper_votes')
def recalc_paper_votes(
    sender,
    instance,
    created,
    update_fields,
    **kwargs
):
    paper = instance.paper
    new_score = paper.calculate_score()
    paper.calculate_hot_score()
    paper.score = new_score
    for author in paper.authors.all():
        score = author.calculate_score()
        author.author_score = score
        author.save()
    paper.save()


@receiver(post_save, sender=Paper, dispatch_uid='pdf_extract_figures')
def queue_extract_figures_from_pdf(
    sender,
    instance,
    created,
    update_fields,
    **kwargs
):
    if instance.figures.all().count() == 0:
        instance.extract_pdf_preview(use_celery=True)
        # instance.extract_figures(use_celery=True)


@receiver(post_save, sender=Paper, dispatch_uid='extract_twitter_comments')
def queue_extract_twitter_comments(
    sender,
    instance,
    created,
    update_fields,
    **kwargs
):
    if created:
        instance.extract_twitter_comments(use_celery=True)


def check_file_updated(update_fields, file):
    if update_fields is not None and file:
        return 'file' in update_fields
    return False
