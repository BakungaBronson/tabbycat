from utils.management.base import TournamentCommand, CommandError
from ...dbutils import add_feedback, add_feedback_to_round, delete_all_feedback_for_round, delete_feedback

from django.contrib.auth.models import User
from tournaments.models import Round
from draw.models import Debate
from adjfeedback.models import AdjudicatorFeedback

OBJECT_TYPE_CHOICES = ["round", "debate"]
SUBMITTER_TYPE_MAP = {
    'tabroom': AdjudicatorFeedback.SUBMITTER_TABROOM,
    'public':  AdjudicatorFeedback.SUBMITTER_PUBLIC
}

class Command(TournamentCommand):

    help = "Adds randomly-generated feedback to the database"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument("type", type=str, choices=OBJECT_TYPE_CHOICES, help="'round' to add feedback to entire round, 'debate' for a particular debate")
        parser.add_argument("specifiers", type=int, nargs="+", help="What to add feedback to. For rounds: seq numbers. For debates: database IDs.")
        parser.add_argument("-p", "--probability", type=float, help="Probability with which to add feedback", default=1.0)
        parser.add_argument("-T", "--submitter-type", type=str, help="Submitter type, either 'tabroom' or 'public'", choices=list(SUBMITTER_TYPE_MAP.keys()), default="tabroom")
        parser.add_argument("-u", "--user", type=str, help="Username of submitter", default="random")

        status = parser.add_mutually_exclusive_group()
        status.add_argument("-D", "--discarded", action="store_true", help="Make feedback discarded")
        status.add_argument("-c", "--confirmed", action="store_true", help="Make feedback confirmed")

        parser.add_argument("--clean", help="Remove all associated feedback first", action="store_true")
        parser.add_argument("--create-user", help="Create user if it doesn't exist", action="store_true")

    @staticmethod
    def _get_user(options):
        if options["submitter_type"] == "public":
            return None
        try:
            return User.objects.get(username=options["user"])
        except User.DoesNotExist:
            if options["create_user"]:
                return User.objects.create_user(options["user"], "", options["user"])
            else:
                raise CommandError("There is no user called {user!r}. Use the --create-user option to create it.".format(user=options["user"]))

    def handle_tournament(self, tournament, **options):
        feedback_kwargs = {
            "submitter_type": SUBMITTER_TYPE_MAP[options["submitter_type"]],
            "user"          : self._get_user(options),
            "probability"   : options["probability"],
            "discarded"     : options["discarded"],
            "confirmed"     : options["confirmed"],
        }

        if options["type"] == "round":
            for seq in options["specifiers"]:
                round = Round.objects.get(tournament=tournament, seq=seq)

                if options["clean"]:
                    self.stdout.write("Deleting all feedback for round {}...".format(round.name))
                    delete_all_feedback_for_round(round)

                self.stdout.write("Generating feedback for round {}...".format(round.name))
                try:
                    add_feedback_to_round(round, **feedback_kwargs)
                except ValueError as e:
                    raise CommandError(e)

        elif options["type"] == "debate":
            for debate_id in options["specifiers"]:
                debate = Debate.objects.get(round__tournament=tournament, id=debate_id)

                if options["clean"]:
                    self.stdout.write("Deleting all feedback for debate {}...".format(debate.matchup))
                    delete_feedback(debate)

                self.stdout.write("Generating feedback for debate {}...".format(debate.matchup))
                try:
                    add_feedback(debate, **feedback_kwargs)
                except ValueError as e:
                    raise CommandError(e)
