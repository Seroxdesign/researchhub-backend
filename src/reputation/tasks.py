import math
import datetime

from celery.decorators import periodic_task
from django.contrib.contenttypes.models import ContentType

from researchhub.settings import REWARD_SCHEDULE, REWARD_TIME, APP_ENV
from researchhub.celery import app
from paper.models import Paper
from reputation.models import Contribution, DistributionAmount
from reputation.distributor import RewardDistributor

DEFAULT_REWARD = 1000000


@app.task
def create_contribution(
    contribution_type,
    instance_type,
    user_id,
    paper_id,
    object_id
):
    content_type = ContentType.objects.get(
        **instance_type
    )
    if contribution_type == Contribution.SUBMITTER:
        create_author_contribution(
            Contribution.AUTHOR,
            user_id,
            paper_id,
            object_id
        )

    previous_contributions = Contribution.objects.filter(
        contribution_type=contribution_type,
        content_type=content_type,
        paper_id=paper_id
    ).order_by(
        'ordinal'
    )

    ordinal = 0
    if previous_contributions.exists():
        ordinal = previous_contributions.last().ordinal + 1

    Contribution.objects.create(
        contribution_type=contribution_type,
        user_id=user_id,
        ordinal=ordinal,
        paper_id=paper_id,
        content_type=content_type,
        object_id=object_id
    )


@app.task
def create_author_contribution(
    contribution_type,
    user_id,
    paper_id,
    object_id
):
    contributions = []
    content_type = ContentType.objects.get(model='author')
    authors = Paper.objects.get(id=paper_id).authors.all()
    for i, author in enumerate(authors.iterator()):
        user = author.user
        data = {
            'contribution_type': contribution_type,
            'ordinal': i,
            'paper_id': paper_id,
            'content_type': content_type,
            'object_id': object_id
        }

        if user:
            data['user'] = user.id

        contributions.append(
            Contribution(**data)
        )
    Contribution.objects.bulk_create(contributions)


@app.task
def distribute_round_robin(paper_id):
    reward_dis = RewardDistributor()
    paper = Paper.objects.get(id=paper_id)
    items = [
        paper.uploaded_by,
        *paper.authors.all(),
        *paper.votes.all(),
        *paper.threads.all()
    ]
    item = reward_dis.get_random_item(items)
    reward_dis.generate_distribution(item, amount=1)
    return items


@periodic_task(
    run_every=REWARD_SCHEDULE,
    priority=3,
    options={'queue': APP_ENV}
)
def distribute_rewards():
    # Checks if rewards should be distributed, given time config
    today = datetime.datetime.today()
    reward_time_hour, reward_time_day, reward_time_week = list(
        map(int, REWARD_TIME.split(' '))
    )

    if reward_time_week:
        week = today.isocalendar()[1]
        if week % reward_time_week != 0:
            return
        # time_delta = datetime.timedelta(weeks=reward_time_week)
    elif reward_time_day:
        day = today.day
        if day % reward_time_day != 0:
            return
        # time_delta = datetime.timedelta(days=reward_time_day)
    elif reward_time_hour:
        hour = today.hour
        if hour % reward_time_hour != 0:
            return
        # time_delta = datetime.timedelta(hours=reward_time_hour)
    else:
        return

    # Reward distribution logic
    last_distribution = DistributionAmount.objects.last()
    starting_date = last_distribution.distributed_date

    # last_week = today - time_delta
    # starting_date = datetime.datetime(
    #     year=last_week.year,
    #     month=last_week.month,
    #     day=last_week.day,
    #     hour=last_week.hour,
    #     minute=last_week.minute,
    #     second=last_week.second
    # )
    reward_dis = RewardDistributor()

    total_reward_amount = DEFAULT_REWARD
    if last_distribution:
        total_reward_amount = last_distribution.amount

    weekly_contributions = Contribution.objects.filter(
        created_date__gt=starting_date,
        created_date__lte=today
    )
    if not weekly_contributions.exists():
        return

    paper_ids = weekly_contributions.values_list('paper')
    papers = Paper.objects.filter(id__in=[paper_ids])
    papers, prob_dist = reward_dis.get_papers_prob_dist(papers)

    reward_distribution = prob_dist * total_reward_amount

    for paper, reward in zip(papers, reward_distribution):
        contribution_count = 0
        contributions = []
        for contribution_tuple in Contribution.contribution_choices:
            contribution_type = contribution_tuple[0]
            filtered_contributions = weekly_contributions.filter(
                paper=paper,
                contribution_type=contribution_type
            )
            contribution_count += filtered_contributions.count()
            contributions.append(filtered_contributions)

        amount = math.floor(reward / contribution_count)
        for qs in contributions:
            for contribution in qs.iterator():
                reward_dis.generate_distribution(contribution, amount=amount)

    last_distribution.distributed = True
    last_distribution.save()
