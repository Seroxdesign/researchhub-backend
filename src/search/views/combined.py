from django.db import IntegrityError
from celery import group
from elasticsearch_dsl import Search
from elasticsearch_dsl.utils import AttrDict
from habanero import Crossref
# from rest_framework.decorators import api_view, permission_classes as perms
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from paper.models import Paper
from researchhub.settings import PAGINATION_PAGE_SIZE
from search.filters import ElasticsearchFuzzyFilter
from search.serializers.combined import CombinedSerializer
from search.tasks import (
    create_authors_from_crossref,
    download_pdf_by_license,
    # search_orcid_author
)
from search.utils import (
    get_crossref_doi,
    get_unique_crossref_items,
    get_crossref_issued_date
)
from utils.permissions import ReadOnly
# from utils.http import RequestMethods


class CombinedView(ListAPIView):
    indices = [
        'paper',
        'author',
        'discussion_thread',
        'hub',
        'summary',
        'university'
    ]
    serializer_class = CombinedSerializer

    permission_classes = [ReadOnly]
    filter_backends = [ElasticsearchFuzzyFilter]

    search_fields = [
        'doi',
        'title',
        'paper_title',
        'first_name',
        'last_name',
        'authors',
        'name',
        'summary_plain_text',
        'plain_text',
    ]

    def __init__(self, *args, **kwargs):
        assert self.indices is not None

        self.search = Search(index=self.indices).highlight(
            *self.search_fields,
            fragment_size=50
        )

        super(CombinedView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        es_search = self.search.query()
        return es_search

    def list(self, request, *args, **kwargs):
        es_response_queryset = self.filter_queryset(self.get_queryset())
        es_response_queryset = [
            hit for hit in es_response_queryset if hit.meta['score'] > 10
        ]

        # NOTE: Not using crossref for now, pending some refinement
        # if request.query_params.get('external_search') != 'false':
        #     es_response_queryset = self._add_crossref_results(
        #         request,
        #         es_response_queryset
        #     )

        page = self.paginate_queryset(es_response_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(es_response_queryset, many=True)
        return Response(serializer.data)

    def _add_crossref_results(self, request, es_response):
        result_space_available = PAGINATION_PAGE_SIZE - len(es_response.hits)

        if result_space_available > 0:
            query = request.query_params.get('search')
            crossref_search_result = search_crossref(query)
            es_dois = self._get_es_dois(es_response.hits)
            crossref_hits = CrossrefHits(
                crossref_search_result,
                es_dois,
                result_space_available
            ).hits
            es_response.hits.extend(crossref_hits)

        return es_response

    def _get_es_dois(self, hits):
        es_papers = filter(lambda hit: (hit.meta['index'] == 'paper'), hits)
        es_dois = [paper['doi'] for paper in es_papers]
        return es_dois


class CrossrefHits:
    def __init__(self, search_result, existing_dois, amount):
        self.items = search_result['message']['items']
        self.existing_dois = existing_dois
        self.amount = amount

        self.remove_duplicate_papers()
        self.hits = self.build_hits()

    def remove_duplicate_papers(self):
        results = []
        for item in self.items:
            doi = get_crossref_doi(item)
            if doi not in self.existing_dois:
                results.append(item)
        self.items = results[:self.amount]

    def build_hits(self):
        hits = []
        for item in self.items:
            meta = self.build_crossref_meta(item)
            paper = self.create_crossref_paper(item)
            if paper:
                hit = AttrDict({
                    'meta': AttrDict(meta),
                    'title': paper.title,
                    'paper_title': paper.paper_title,
                    'doi': paper.doi,
                    'url': paper.url,
                    'id': paper.id,
                })
                hits.append(hit)
        return hits

    def build_crossref_meta(self, item):
        # TODO: Add highlight
        return {
            'index': 'crossref_paper',
            'id': None,
            'score': -1,
            'highlight': None,
        }

    def create_crossref_paper(self, item):
        try:
            paper = Paper.objects.create(
                title=item['title'][0],
                paper_title=item['title'][0],
                doi=item['DOI'],
                url=item['URL'],
                paper_publish_date=get_crossref_issued_date(item),
                retrieved_from_external_source=True
            )
            tasks = [download_pdf_by_license.signature((item, paper.id))]
            try:
                authors = item['author']
                if len(authors) > 0:
                    tasks.append(
                        create_authors_from_crossref.signature(
                            (authors, paper.id, paper.doi)
                        )
                    )
            except KeyError:
                pass
            job = group(tasks)
            job.apply_async()
            return paper
        except IntegrityError:
            pass


# Debugging
# @api_view([RequestMethods.GET])
# @perms([ReadOnly])
# def crossref(request):
#     query = request.query_params.get('query')
#     results = search_crossref(query)
#     return Response(results)


def search_crossref(query):
    results = []
    cr = Crossref()
    filters = {'type': 'journal-article'}
    limit = 10
    offset = 0
    count = 0
    trial_limit = 2
    trials = 0

    # Try to get `limit` unique results
    while (count < limit) and (trials < trial_limit):
        trials += 1
        results = cr.works(
            query_bibliographic=query,
            limit=limit,
            offset=offset,
            filter=filters,
            select=[
                'DOI',
                'title',
                'issued',
                'author',
                'score',
                'URL',
            ],
            sort='score',  # relevance
            order='desc'
        )
        results['message']['items'] = get_unique_crossref_items(
            results['message']['items']
        )
        offset += limit
        count += len(results['message']['items'])

    return results

# Debugging
# @api_view([RequestMethods.GET])
# @perms([ReadOnly])
# def orcid(request):
#     results = search_orcid_author('Rodney', 'Garratt')
#     return Response(results)
