from utils.permissions import AuthorizationBasedPermission, RuleBasedPermission


class CreatePaper(RuleBasedPermission):
    message = 'Not enough reputation to upload paper.'

    def satisfies_rule(self, request):
        return request.user.reputation >= 1


# TODO: Implement
class UpdatePaper(AuthorizationBasedPermission):
    message = 'Action not permitted.'

    def is_authorized(self, request):
        # user is author, moderator, or creator
        pass


class FlagPaper(RuleBasedPermission):
    message = 'Not enough reputation to flag paper.'

    def satisfies_rule(self, request):
        return request.user.reputation >= 50


class UpvotePaper(RuleBasedPermission):
    message = 'Not enough reputation to upvote paper.'

    def satisfies_rule(self, request):
        return request.user.reputation >= 1


class DownvotePaper(RuleBasedPermission):
    message = 'Not enough reputation to upvote paper.'

    def satisfies_rule(self, request):
        return request.user.reputation >= 25


# TODO: Implement assign moderator functionality
class AssignModerator(AuthorizationBasedPermission):

    def is_authorized(self, request):
        # user is author
        pass
